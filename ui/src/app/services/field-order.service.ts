import { Attribute, Injectable } from '@angular/core';
import { MetadataService, EntityMetadata } from './metadata.service';

@Injectable({
  providedIn: 'root'
})

// DFA - DisplayFieldAfter Attribute
// Algorithm:
//    The concept is to use a field (DisplayFieldAfter) to determine the order of fields in a form.
//    Also, id fields have a special treatment as do fields with negative DFA.
//
//  High Level Steps:
// 1. Honor any DFA chains
// 2. Sort fields not in a DFA chain by their field name
// 3. If _id (PK) is not in a DFA chain, place it first
// 4. Place fields with no DFA (ingore ID fields)
// 5. Insert DFA chains based on the name of the first field.
// 6. If any ID fields remain (FK), place them at the end of the list in field name order.
// 7. Place any negative DFA fields at the end of the list starting with -1, -2, -3, etc.


export class FieldOrderService {

  constructor(private metadataService: MetadataService) {}
  orderFields(fields: string[], metadata: EntityMetadata): string[] {
    // --- Preparation --------------------------------------------------------
    const unused = new Set(fields);                    // cheap “membership” checks
    const dfaPairs = new Map<string, string>();        // key → field that follows it
    const negativeDFAs: Array<[string, number]> = [];  // [field, -N]
    const idFields: string[] = [];

    // --- 1. Categorise fields ----------------------------------------------
    for (const field of fields) {
      const dfa = metadata.fields[field]?.ui?.displayAfterField ?? '';

      if (dfa) {
        // 1a. Negative positions
        if (dfa.startsWith('-')) {
          const n = Number(dfa);
          if (Number.isNaN(n))
            throw new Error(`Invalid negative DFA "${dfa}" on field ${field}`);
          negativeDFAs.push([field, n]);
          unused.delete(field);

        // 1b. Normal DFA chains
        } else if (fields.includes(dfa)) {
          dfaPairs.set(dfa, field);   // “insert <field> after <dfa>”
          unused.delete(field);
        }
      }
    }

    // --- 2. Seed ordered list ----------------------------------------------
    const ordered: string[] = [];

    // 2a. _id first (if not part of a DFA chain)
    if (unused.has('_id')) {
      ordered.push('_id');
      unused.delete('_id');
    }

    // 2b. Other “…Id” fields without DFA → staged for later insertion
    for (const f of Array.from(unused)) {
      if (f.toLowerCase().endsWith('id')) {
        idFields.push(f);
        unused.delete(f);
      }
    }

    // 2c. Plain fields, alphabetically
    ordered.push(...Array.from(unused).sort());
    unused.clear();         // nothing left to process

    // --- 3. Honour DFA chains ----------------------------------------------
    for (const [before, after] of dfaPairs) {
      const idx = ordered.indexOf(before);
      if (idx !== -1) ordered.splice(idx + 1, 0, after);
      else             ordered.push(after);   // fallback if “before” was itself in a chain
    }

    // --- 4. Append staged Id fields ----------------------------------------
    ordered.push(...idFields.sort());

    // --- 5. Append negative DFA fields in -1, -2, … order ------------------
    negativeDFAs
      .sort((a, b) => a[1] - b[1])
      .forEach(([field]) => ordered.push(field));

    return ordered;
  }
}