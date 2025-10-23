from pathlib import Path
import sys
import traceback
from typing import Dict, Set, Any, List, Tuple, Optional

import json5
import yaml

# ---------------- YAML helpers ---------------- #
class QuotedStr(str):
    """String that will be quoted in YAML output"""
    pass

def quoted_str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

yaml.add_representer(QuotedStr, quoted_str_representer)

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

# ---------------- Parser ---------------- #

FIELD_KEY = 'fields'
UI_KEY = 'ui'
OPERATIONS = {"create": "c", "read": "r", "update": "u", "delete": "d"}

class SchemaParser:
    """Multipass MMD parser that handles forward references and robust decorator parsing."""

    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Tuple[str, str]] = []
        self.dictionaries: Dict[str, Dict[str, Any]] = {}
        # staging areas collected in pass 2
        self._entity_level_decorators: Dict[str, List[str]] = {}
        self._field_level_decorators: Dict[Tuple[str, str], List[str]] = {}

    # ---------- public API ---------- #
    def parse_mmd1(self, file_name: str) -> Tuple[Dict[str, Any], List[Tuple[str, str]], Dict[str, Any]]:
        with open(file_name, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Pass 0: dictionaries (global)
        self._extract_dictionary_entries(lines)

        # Pass 1: entity shells + fields (store raw decorators without applying)
        self._extract_entities_and_fields(lines)

        # Pass 2: relationships (after we know all entity names)
        self._extract_relationships(lines)
        self._materialize_relationship_fields()

        # Pass 3: apply decorators (entity then field) — robust parser for multiple decorators per line and JSON spacing
        self._apply_entity_decorators()
        self._apply_field_decorators()

        return self.entities, self.relationships, self.dictionaries

    # ---------- passes ---------- #
    def _extract_dictionary_entries(self, lines: List[str]) -> None:
        for raw in lines:
            line = raw.strip()
            if not line.startswith('%%'):
                continue
            # support both "%%@dictionary" and "%% @dictionary"
            if '@dictionary' in line:
                # format: %% @dictionary <name> { ...json... }
                after = line.split('@dictionary', 1)[1].strip()
                parts = after.split(None, 1)
                if not parts:
                    continue
                dict_name = parts[0]
                json_text = parts[1].strip() if len(parts) > 1 else '{}'
                try:
                    data = json5.loads(json_text)
                    if isinstance(data, dict):
                        self.dictionaries.setdefault(dict_name, {}).update(data)
                except Exception as e:
                    raise ValueError(f"Dictionary parse error for '{dict_name}': {e}\nLine: {line}")

    def _extract_entities_and_fields(self, lines: List[str]) -> None:
        cur: Optional[str] = None
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            # entity open:  EntityName {   (optionally followed by decorators on same line)
            if line.endswith('{') and not line.startswith('%'):
                words = line[:-1].strip().split()
                if not words:
                    continue
                entity = words[0]
                cur = entity
                self.entities[entity] = {FIELD_KEY: {}, 'relationships': []}
                # if there are trailing tokens (e.g., 'Entity { %% @abstract') store them as decorators text
                tail = line[line.find('{')+1:].strip()
                if tail:
                    self._entity_level_decorators.setdefault(entity, []).append(tail)
                continue

            if cur and line == '}':
                cur = None
                continue

            if cur:
                if line.startswith('%%'):
                    # entity-level decorator line (may contain multiple decorators)
                    self._entity_level_decorators.setdefault(cur, []).append(line)
                else:
                    # field line:  Type name  [%% @decorators ...]
                    parts = line.split()
                    if len(parts) >= 2:
                        ftype, fname = parts[0], parts[1]
                        self.entities[cur][FIELD_KEY].setdefault(fname, {"type": ftype})
                        rest = line.split(fname, 1)[1]
                        if '%%' in rest or '@' in rest:
                            self._field_level_decorators.setdefault((cur, fname), []).append(rest)

    def _extract_relationships(self, lines: List[str]) -> None:
        for raw in lines:
            s = raw.strip()
            if '||--o{' in s:
                left, right = s.split('||--o{', 1)
                src = left.strip()
                # allow optional label after ':'
                tgt = right.split(':', 1)[0].strip().rstrip('}')
                self.relationships.append((src, tgt))

    def _materialize_relationship_fields(self) -> None:
        for src, tgt in self.relationships:
            if tgt not in self.entities:
                # forward ref of entity names handled because pass 1 already collected shells
                continue
            fields = self.entities[tgt].setdefault(FIELD_KEY, {})
            fk = f"{src}Id" if src and src[0].isupper() else f"{(src or '').capitalize()}Id"
            value = {"type": "ObjectId", "required": True}
            if fk in fields and isinstance(fields[fk], dict):
                fields[fk].update(value)
            else:
                fields[fk] = value

    # ---------- decorator application ---------- #
    def _apply_entity_decorators(self) -> None:
        for entity, chunks in self._entity_level_decorators.items():
            for chunk in chunks:
                for dec_name, payload, field_hint in self._tokenize_decorators(chunk):
                    # Effective payload: prefer JSON payload, otherwise bare token
                    eff = (payload or field_hint or '').strip()

                    if dec_name == 'abstract':
                        self.entities[entity]['abstract'] = True

                    elif dec_name == 'include':
                        if eff:
                            self._apply_include(entity, eff)

                    elif dec_name == 'service':
                        if eff:
                            self.entities[entity].setdefault('service', []).append(eff)

                    elif dec_name == 'operations':
                        op = self._ops_shorthand(eff) if eff else ''
                        if op:
                            self.entities[entity].setdefault('operations', op)

                    elif dec_name == 'ui':
                        data = self._safe_json(eff)
                        if isinstance(data, dict):
                            self.entities[entity].setdefault(UI_KEY, {}).update(data)

                    elif dec_name == 'unique':
                        if eff:
                            fields = [p.strip() for p in eff.split('+')]
                            self.entities[entity].setdefault('unique', []).append(fields)

                    elif dec_name == 'show':
                        if eff:
                            self._apply_show(self.entities[entity], eff)

    def _apply_field_decorators(self) -> None:
        for (entity, field), chunks in self._field_level_decorators.items():
            for chunk in chunks:
                for dec_name, payload, field_hint in self._tokenize_decorators(chunk):
                    name = field_hint or field
                    eff = (payload or '').strip()

                    if dec_name == 'validate':
                        data = self._safe_json(eff)
                        if isinstance(data, dict):
                            self.entities[entity][FIELD_KEY].setdefault(name, {}).update(data)

                    elif dec_name == 'ui':
                        data = self._safe_json(eff)
                        if isinstance(data, dict):
                            fld = self.entities[entity][FIELD_KEY].setdefault(name, {})
                            # Only allow 'show' on ObjectId (matches previous behavior)
                            if 'show' in data and fld.get('type', 'ObjectId') != 'ObjectId':
                                data = {k: v for k, v in data.items() if k != 'show'}
                            fld.setdefault(UI_KEY, {}).update(data)

                    elif dec_name == 'unique':
                        # allow field-level unique (single or part of composite if payload contains +)
                        if eff and '+' in eff:
                            fields = [p.strip() for p in (name + '+' + eff).split('+')]
                        else:
                            fields = [name]
                        self.entities[entity].setdefault('unique', []).append(fields)

    # ---------- helpers ---------- #
    def _safe_json(self, text: Optional[str]) -> Any:
        if text is None:
            return {}
        if isinstance(text, (dict, list)):
            return text
        s = str(text).strip()
        if not s:
            return {}
        try:
            return json5.loads(s)
        except Exception as e:
            raise ValueError(f"JSON parse error: {e}. Offending text: {text}")

    def _ops_shorthand(self, text: Optional[str]) -> str:
        if text is None:
            return ''
        t = str(text).strip()
        if not t:
            return ''
        # fast-path: bare shorthand like "cru"
        if t[0] not in '[{' and not (t.startswith('"') and t.endswith('"')):
            return t
        try:
            val = json5.loads(t)
            if isinstance(val, list):
                return ''.join(OPERATIONS.get(x.lower(), '') for x in val)
            if isinstance(val, str):
                return val
        except Exception:
            pass
        return ''

    def _apply_include(self, entity: str, payload: str) -> None:
        if not payload:
            return
        words = payload.strip().split()
        if not words:
            return
        base = words[0]
        display_after: Optional[str] = None
        # allow optional trailing ui decorator for displayAfterField control
        if '@ui' in payload:
            try:
                after = payload.split('@ui', 1)[1]
                data = self._safe_json(after)
                if isinstance(data, dict):
                    display_after = data.get('displayAfterField')
            except Exception:
                pass
        src = self.entities.get(base)
        if not src or FIELD_KEY not in src:
            raise ValueError(f"@include refers to unknown abstraction '{base}'")
        dst = self.entities[entity]
        # copy unique/relationships/service
        dst.setdefault('unique', []).extend(src.get('unique', []))
        dst.setdefault('relationships', []).extend(src.get('relationships', []))
        dst.setdefault('service', []).extend(src.get('service', []))
        # deep copy fields
        import copy as _copy
        fields_copy = _copy.deepcopy(src[FIELD_KEY])
        if display_after is None or display_after != '':
            prior = -1
            daf = display_after if display_after is not None else str(prior)
            for v in fields_copy.values():
                v.setdefault(UI_KEY, {}).update({'displayAfterField': daf})
                prior -= 1
        dst.setdefault(FIELD_KEY, {}).update(fields_copy)

    def _apply_show(self, entity_obj: Dict[str, Any], payload: str) -> None:
        if not payload:
            return
        words = payload.strip().split()
        if not words:
            return
        foreign = words[0]
        data = self._safe_json(' '.join(words[1:])) if len(words) > 1 else {}
        key = foreign[0].lower().capitalize() + foreign[1:] + 'Id'
        fields = entity_obj.setdefault(FIELD_KEY, {})
        kf = fields.setdefault(key, {})
        show = kf.setdefault('show', {})
        endpoint = data.get('endpoint', foreign).lower()
        show['endpoint'] = endpoint
        display_info = show.setdefault('displayInfo', [])
        for cfg in data.get('displayInfo', []):
            dp = cfg.get('displayPages')
            fl = cfg.get('fields')
            if dp and fl:
                display_info.append({"displayPages": dp, "fields": fl})

    def _tokenize_decorators(self, text: str) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """
        Yield tuples of (decorator_name_without_at, payload_text_or_None, field_hint_if_any)
        Handles multiple decorators per line and tolerant spacing like "}," vs "} ,".
        We do a bracket-aware scan so JSON/arrays can contain braces/commas safely.
        Also supports entity-level field hint syntax: "@ui fieldName { ... }".
        """
        out: List[Tuple[str, Optional[str], Optional[str]]] = []
        s = text
        # normalize possible leading '%%' and extra spaces
        if s.startswith('%%'):
            s = s[2:].lstrip()
        # repeatedly find '@'
        i = 0
        n = len(s)
        while i < n:
            at = s.find('@', i)
            if at == -1:
                break
            j = at + 1
            # decorator name
            while j < n and s[j].isalpha():
                j += 1
            name = s[at+1:j]
            # skip spaces
            k = j
            while k < n and s[k].isspace():
                k += 1
            # optional field hint (one bare token not starting with '{' or '[')
            field_hint = None
            if k < n and s[k] not in '{[':
                # read token until space or start of json
                m = k
                while m < n and not s[m].isspace() and s[m] not in '@{[':
                    m += 1
                token = s[k:m]
                # if token looks like a JSON start, treat as none
                if token and not token.startswith('%') and token != ',':
                    field_hint = token
                k = m
                while k < n and s[k].isspace():
                    k += 1
            # optional JSON/array payload
            payload = None
            if k < n and s[k] in '{[':
                start = k
                depth = 0
                q = None
                p = k
                while p < n:
                    ch = s[p]
                    if q:
                        if ch == q and s[p-1] != '\\':
                            q = None
                    else:
                        if ch in '"\'':
                            q = ch
                        elif ch in '{[':
                            depth += 1
                        elif ch in '}]':
                            depth -= 1
                            if depth == 0:
                                p += 1
                                break
                    p += 1
                payload = s[start:p]
                k = p
            # advance to next '@' (skip optional commas/spaces)
            while k < n and s[k] in ' ,':
                k += 1
            i = k
            out.append((name, payload, field_hint))
        return out

# ---------------- conversion driver ---------------- #

def extract_entities_metadata(entities: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    services: Set[str] = set()
    includes: Set[str] = set()
    for _name, data in entities.items():
        for item in data.get('include', []) or []:
            if isinstance(item, str):
                includes.add(item)
        for item in data.get('service', []) or []:
            if isinstance(item, str):
                services.add(item)
    return services, includes


def generate_yaml_object(entities, relationships, dictionaries, services, includes):
    top_relationships = []
    for source, target in relationships:
        top_relationships.append({"source": source, "target": target})
        if source in entities:
            entities.setdefault(source, {}).setdefault('relationships', [])
            if target not in entities[source]['relationships']:
                entities[source]['relationships'].append(target)

    return {
        "_relationships": top_relationships,
        "_dictionaries": dictionaries,
        "_services": list(services),
        "_included_entities": list(includes),
        "_entities": entities,
    }


def convert_schema(schema_path: str) -> Optional[str]:
    try:
        yaml.add_representer(QuotedStr, quoted_str_representer)
        print(f"Reading schema from {schema_path}")
        parser = SchemaParser()
        print("Parsing schema (multipass).")
        entities, relationships, dictionaries = parser.parse_mmd1(schema_path)
        services, includes = extract_entities_metadata(entities)
        output_obj = generate_yaml_object(entities, relationships, dictionaries, services, includes)
        out_file = schema_path.replace('.mmd', '.yaml')
        print(f"Writing YAML to {out_file}.  Generated {len(entities)} entities")
        with open(out_file, 'w') as f:
            yaml.dump(output_obj, f, sort_keys=False, default_flow_style=False, Dumper=NoAliasDumper)
        return out_file
    except Exception as e:
        print(f"Error converting schema: {e}")
        traceback.print_exc()
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python schemaConvert_new.py <schema.mmd>')
        sys.exit(1)
    convert_schema(sys.argv[1])
