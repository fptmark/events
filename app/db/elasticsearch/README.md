# Elasticsearch Template and Query Strategy

## Overview

This document describes the simplified Elasticsearch template and query approach for column-based filtering with wildcard support and case-insensitive matching.

## Template Structure

```json
{
  "index_patterns": ["*"],
  "settings": {
    "analysis": {
      "normalizer": {
        "lc": {
          "type": "custom",
          "char_filter": [],
          "filter": ["lowercase"]
        }
      }
    }
  },
  "mappings": {
    "dynamic_templates": [
      {
        "strings": {
          "match_mapping_type": "string",
          "mapping": {
            "type": "keyword",
            "normalizer": "lc"
          }
        }
      }
    ]
  }
}
```

## Field Types

| Field Type | ES Type | Normalizer | Example Values |
|------------|---------|------------|----------------|
| String | keyword | lc (lowercase) | "John", "Smith" |
| Integer | long | none | 25, 100 |
| Decimal | double | none | 25.5, 99.99 |
| Date | date | none | "2024-01-15" |

## Query Capabilities

### String Queries (Wildcard)

| Pattern | Query | Matches | Example |
|---------|-------|---------|---------|
| Exact | `{"wildcard": {"firstName": "john"}}` | "John" | john → John |
| Prefix | `{"wildcard": {"firstName": "jo*"}}` | "John", "Jonathan" | jo* → John, Jonathan |
| Suffix | `{"wildcard": {"firstName": "*son"}}` | "Johnson", "Peterson" | *son → Johnson |
| Contains | `{"wildcard": {"firstName": "*oh*"}}` | "John", "Cohen" | *oh* → John, Cohen |

### Numeric Queries (Range/Term)

| Pattern | Query | Matches | Example |
|---------|-------|---------|---------|
| Exact | `{"term": {"age": 25}}` | 25 | 25 → exactly 25 |
| Greater | `{"range": {"age": {"gt": 25}}}` | 26, 27, 28... | >25 → 26+ |
| Less | `{"range": {"age": {"lt": 30}}}` | 29, 28, 27... | <30 → up to 29 |
| Range | `{"range": {"age": {"gte": 25, "lte": 30}}}` | 25-30 | 25-30 → inclusive |

## Use Cases Supported

✅ **Column header filtering with wildcards**
- Input boxes above columns with optional `*` wildcards
- Case-insensitive string matching
- Exact and range numeric filtering

✅ **Sorting and aggregations**
- Multi-field sorting with case-insensitive ordering
- Terms aggregations for faceted search

✅ **Simple field naming**
- Direct field names (`firstName`, `age`) - no `.raw` suffixes
- Clean query structure

## Use Cases Not Supported

❌ **Full-text search**
- No tokenization or analysis
- Can't search "John Smith" across `firstName` and `lastName` fields

❌ **Fuzzy matching**
- No typo tolerance ("Jon" won't find "John")
- No stemming or synonym support

❌ **Complex pattern matching**
- Limited to basic wildcards (`*` only)
- No regex or boolean pattern combinations

❌ **Relevance scoring**
- All matches are equal - no ranking by relevance

## Performance Characteristics

### Storage (10 columns, 8 strings)
- **100K rows**: ~50% smaller than dual-field (text + keyword) approach
- **1M rows**: Significant storage savings, faster indexing

### Query Performance
- **Exact matching**: Very fast (hash lookup)
- **Prefix wildcards** (`jo*`): Fast (optimized in Lucene)
- **Suffix wildcards** (`*son`): Slower but acceptable (<500ms at 1M rows)
- **Contains wildcards** (`*oh*`): Moderate performance
- **Leading wildcards**: Inherently slower, avoid if possible

### Recommendations
- Use prefix wildcards when possible for best performance
- Limit wildcard usage on very large text fields
- Consider pagination for large result sets

## API Integration

Column filters should:
1. Detect input pattern (exact vs wildcard)
2. Choose query type based on field type (string vs numeric)
3. Apply case-insensitive wildcard for strings
4. Apply range/term queries for numbers

Example API query translation:
- `firstName: "jo*"` → `{"wildcard": {"firstName": "jo*"}}`
- `age: ">25"` → `{"range": {"age": {"gt": 25}}}`
- `status: "active"` → `{"wildcard": {"status": "active"}}`