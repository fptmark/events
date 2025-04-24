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
    const fieldMeta = metadata.fields || {};
    const placed = new Set<string>();
    const chains: Record<string, string[]> = {};
    const dangling: string[] = [];
    const idFields: string[] = [];
    const negativeDFAMap: Record<string, string[]> = {};
    const noDFA: string[] = [];
  
    // Categorize fields
    for (const field of fields) {
      const dfa = fieldMeta[field]?.ui?.displayAfterField ?? '';
      if (dfa.startsWith('-')) {
        if (!negativeDFAMap[dfa]) negativeDFAMap[dfa] = [];
        negativeDFAMap[dfa].push(field);
      } else if (dfa) {
        if (!chains[dfa]) chains[dfa] = [];
        chains[dfa].push(field);
      } else {
        noDFA.push(field);
      }
    }
  
    for (const key in chains) chains[key].sort();
    for (const key in negativeDFAMap) negativeDFAMap[key].sort();
  
    const validFields = new Set(fields);
    for (const start of Object.keys(chains)) {
      if (!validFields.has(start)) {
        dangling.push(...chains[start]);
        delete chains[start];
      }
    }
    dangling.sort();
  
    // Separate Id fields
    const noDFAFields = noDFA.filter(f => {
      if (f !== '_id' && f.endsWith('Id')) {
        idFields.push(f);
        return false;
      }
      return true;
    }).sort();
    idFields.sort();
  
    const ordered: string[] = [];
  
    // Place _id first if no DFA
    if (fields.includes('_id') && (fieldMeta['_id']?.ui?.displayAfterField ?? '') === '') {
      ordered.push('_id');
      placed.add('_id');
    }
  
    // Place no-DFA fields
    for (const f of noDFAFields) {
      if (!placed.has(f)) {
        ordered.push(f);
        placed.add(f);
      }
    }
  
    // Place Id fields
    for (const f of idFields) {
      if (!placed.has(f)) {
        ordered.push(f);
        placed.add(f);
      }
    }
  
    // Place dangling DFAs
    for (const f of dangling) {
      if (!placed.has(f)) {
        ordered.push(f);
        placed.add(f);
      }
    }
  
    // Recursive chain inserter
    const insertChain = (start: string) => {
      if (placed.has(start)) return;
      ordered.push(start);
      placed.add(start);
      if (chains[start]) {
        for (const next of chains[start]) {
          insertChain(next);
        }
      }
    };
  
    // Place DFA chains (valid)
    for (const start in chains) {
      insertChain(start);
    }
  
    // Place negative DFA chains
    const sortedNegatives = Object.keys(negativeDFAMap).sort((a, b) => parseInt(b) - parseInt(a));
    for (const neg of sortedNegatives) {
      for (const field of negativeDFAMap[neg]) {
        insertChain(field);
      }
    }
    return ordered;
  }

}