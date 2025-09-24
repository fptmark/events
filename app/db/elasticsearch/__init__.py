"""
Elasticsearch database driver implementation.
"""

from ..base import DatabaseInterface
from .core import ElasticsearchCore, ElasticsearchEntities, ElasticsearchIndexes
from .documents import ElasticsearchDocuments


class ElasticsearchDatabase(DatabaseInterface):
    """Elasticsearch implementation of DatabaseInterface"""
    
    def _get_manager_classes(self) -> dict:
        """Return Elasticsearch manager classes"""
        return {
            'core': ElasticsearchCore,
            'documents': ElasticsearchDocuments,
            'entities': ElasticsearchEntities,
            'indexes': ElasticsearchIndexes
        }
    
    async def supports_native_indexes(self) -> bool:
        """Elasticsearch does not support native unique indexes"""
        return False

    async def wipe_and_reinit(self) -> bool:
        """Completely wipe all indices and reinitialize with correct mappings"""
        try:
            self._ensure_initialized()
            es = self.core.get_connection()

            # Get all current indices (excluding system indices)
            indices_response = await es.cat.indices(format="json")
            user_indices = [idx["index"] for idx in indices_response if not idx["index"].startswith(".")]

            # Delete all user indices
            for index_name in user_indices:
                await es.indices.delete(index=index_name, ignore=[404])

            # Delete old template if it exists
            await es.indices.delete_index_template(name="app-text-raw-template", ignore=[404])
            await es.indices.delete_index_template(name="app-keyword-template", ignore=[404])

            # Recreate template with current settings
            await self.core._ensure_index_template()

            # Reset health state to healthy after successful cleanup
            self._health_state = "healthy"

            return True

        except Exception as e:
            import logging
            logging.error(f"Database wipe and reinit failed: {e}")
            return False

    async def get_status_report(self) -> dict:
        """Get comprehensive database status including mapping validation"""
        try:
            self._ensure_initialized()
            es = self.core.get_connection()

            # Get cluster info
            cluster_info = await es.info()

            # Get all indices
            indices_response = await es.cat.indices(format="json")
            user_indices = [idx for idx in indices_response if not idx["index"].startswith(".")]

            # Check mappings for violations
            violations = []
            indices_details = {}

            for idx in user_indices:
                index_name = idx["index"]
                doc_count = int(idx["docs.count"]) if idx["docs.count"] else 0
                store_size = idx["store.size"] if idx["store.size"] else "0b"

                try:
                    # Get mapping
                    mapping_response = await es.indices.get_mapping(index=index_name)
                    properties = mapping_response.get(index_name, {}).get("mappings", {}).get("properties", {})

                    # Analyze each field
                    fields = {}
                    for field_name, field_mapping in properties.items():
                        if field_name in ["id", "_id"]:
                            continue

                        field_status = "ok"
                        es_type = field_mapping.get("type", "unknown")

                        # Get schema type and enum info from metadata
                        schema_type = "unknown"
                        is_enum = False
                        try:
                            from app.services.metadata import MetadataService
                            # Get entity name from index name (capitalize first letter)
                            entity_name = index_name.capitalize()
                            schema_type = MetadataService.get(entity_name, field_name, 'type') or "unknown"
                            field_metadata = MetadataService.get(entity_name, field_name)
                            if field_metadata:
                                is_enum = "enum" in field_metadata
                        except:
                            pass

                        # Format type display as es_type/schema_type
                        type_display = f"{es_type}/{schema_type}"

                        # Check for violations
                        if field_mapping.get("type") == "text" and "fields" in field_mapping:
                            field_status = "uses old text+.raw mapping"
                            violations.append(f"{index_name}.{field_name}: {field_status}")
                        elif field_mapping.get("type") == "keyword" and field_mapping.get("normalizer") != "lc":
                            field_status = "keyword field missing 'lc' normalizer"
                            violations.append(f"{index_name}.{field_name}: {field_status}")

                        # Get field statistics
                        population = "0%"
                        approx_uniques = "0%"

                        if doc_count > 0:
                            try:
                                # Get field stats using exists query for population
                                exists_query = {
                                    "query": {"exists": {"field": field_name}},
                                    "size": 0
                                }
                                exists_response = await es.search(index=index_name, body=exists_query)
                                non_null_count = exists_response.get("hits", {}).get("total", {}).get("value", 0)
                                population_pct = int((non_null_count / doc_count) * 100)
                                population = f"{population_pct}%"

                                # Get cardinality using cardinality aggregation
                                if non_null_count > 0:
                                    # Choose the right field for cardinality based on type
                                    cardinality_field = field_name
                                    if es_type == "text" and "fields" in field_mapping and "raw" in field_mapping["fields"]:
                                        cardinality_field = f"{field_name}.raw"

                                    cardinality_query = {
                                        "aggs": {
                                            "unique_count": {
                                                "cardinality": {"field": cardinality_field}
                                            }
                                        },
                                        "size": 0
                                    }
                                    cardinality_response = await es.search(index=index_name, body=cardinality_query)
                                    unique_count = cardinality_response.get("aggregations", {}).get("unique_count", {}).get("value", 0)
                                    if unique_count > 0:
                                        cardinality_pct = int((unique_count / non_null_count) * 100)
                                        approx_uniques = f"{cardinality_pct}%"

                            except Exception as stats_error:
                                # Stats failed, use defaults
                                import logging
                                logging.warning(f"Field stats failed for {index_name}.{field_name}: {stats_error}")

                        # For enums, flag high uniqueness as potential issue
                        approx_uniques_display = approx_uniques
                        if is_enum and approx_uniques != "0%":
                            # Extract percentage value for comparison
                            uniques_pct = int(approx_uniques.rstrip('%'))
                            if uniques_pct > 50:
                                approx_uniques_display = f"🔴{approx_uniques}"

                        fields[field_name] = {
                            "type": type_display,
                            "status": field_status,
                            "population": population,
                            "approx_uniques": approx_uniques_display,
                            "is_enum": is_enum
                        }

                    indices_details[index_name] = {
                        "doc_count": doc_count,
                        "store_size": store_size,
                        "fields": fields
                    }

                except Exception as e:
                    indices_details[index_name] = {
                        "error": f"Could not analyze: {str(e)}"
                    }

            # Check template status - simplified
            template_ok = True
            try:
                # Check if correct template exists
                template_response = await es.indices.get_index_template(name="app-keyword-template")
                has_new_template = len(template_response.get("index_templates", [])) > 0

                # Check if old conflicting template exists
                old_template_response = await es.indices.get_index_template(name="app-text-raw-template")
                has_old_template = len(old_template_response.get("index_templates", [])) > 0

                # Template is OK only if we have new template and no old template
                template_ok = has_new_template and not has_old_template

            except:
                template_ok = False

            # Determine overall status
            if not template_ok or len(violations) > 0:
                status = "degraded"
            else:
                status = "success"

            return {
                "database": "elasticsearch",
                "status": status,
                "template_ok": template_ok,
                "cluster": {
                    "name": cluster_info.get("cluster_name", "unknown"),
                    "version": cluster_info.get("version", {}).get("number", "unknown")
                },
                "indices": {
                    "total": len(user_indices),
                    "details": indices_details
                },
                "mappings": {
                    "violations_count": len(violations),
                    "violations": violations
                }
            }

        except Exception as e:
            return {
                "database": "elasticsearch",
                "status": "failure",
                "error": str(e)
            }


__all__ = ['ElasticsearchDatabase']