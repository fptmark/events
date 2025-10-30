#!/usr/bin/env python3
"""
Schema Extractor - Reverse engineer database schema to MMD

Usage:
    python tools/schema_extractor/main.py mongo.json -v
    python tools/schema_extractor/main.py mongo.json -v -o mongo.mmd
    python tools/schema_extractor/main.py mongo.json -v -o custom_schema
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import Config
from app.db import DatabaseFactory
from tools.schema_extractor.introspector import DatabaseIntrospector
from tools.schema_extractor.analyzer import SchemaAnalyzer
from tools.schema_extractor.generators.mmd import MMDGenerator


async def main():
    """Main entry point for schema extractor"""
    parser = argparse.ArgumentParser(description='Extract database schema to MMD format')
    parser.add_argument('config', nargs='?', default='mongo.json',
                       help='Configuration file path (default: mongo.json)')
    parser.add_argument('--output', '-o', default=None,
                       help='Output file name (default: config_name.mmd). If no .mmd extension, will append it.')
    parser.add_argument('--sample-size', type=int, default=100,
                       help='Number of documents to sample for analysis (default: 100)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Determine output filename
    if args.output:
        # User specified output - ensure .mmd extension
        if args.output.endswith('.mmd'):
            output_base = args.output[:-4]  # Remove .mmd to get base name
        else:
            output_base = args.output
    else:
        # Default: use config filename (mongo.json -> mongo)
        config_path = Path(args.config)
        output_base = config_path.stem  # Gets filename without extension

    # Initialize config
    print(f"Loading configuration from: {args.config}")
    Config.initialize(args.config)

    # Get database parameters
    db_type, db_uri, db_name = Config.get_db_params()
    case_sensitive = Config.get('case_sensitive', False)

    if not db_type or not db_uri or not db_name:
        print("Error: Missing database configuration")
        sys.exit(1)

    print(f"Connecting to {db_type} database: {db_name}")

    try:
        # Initialize database connection
        db = await DatabaseFactory.initialize(db_type, db_uri, db_name, case_sensitive)

        # Step 1: Introspect database schema
        print("\n[1/3] Introspecting database schema...")
        introspector = DatabaseIntrospector(db, verbose=args.verbose)
        schema = await introspector.extract_schema()

        if args.verbose:
            print(f"  Found {len(schema)} collections/tables")

        # Step 2: Analyze data for enums, validation rules, etc.
        print("\n[2/3] Analyzing data patterns...")
        analyzer = SchemaAnalyzer(db, sample_size=args.sample_size, verbose=args.verbose)
        enriched_schema = await analyzer.analyze_schema(schema)

        # Step 3: Generate MMD file
        print("\n[3/3] Generating MMD file...")
        mmd_gen = MMDGenerator(enriched_schema)
        mmd_output = f"{output_base}.mmd"
        mmd_gen.generate(mmd_output)
        print(f"  ✓ Generated: {mmd_output}")

        print(f"\n✅ Schema extraction complete!")
        print(f"   Output: {mmd_output}")
        print(f"   Use your MMD->YAML tooling to convert to schema.yaml format")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    finally:
        # Close database connection
        if DatabaseFactory.is_initialized():
            await DatabaseFactory.close()


if __name__ == "__main__":
    asyncio.run(main())
