# kgraphing Schema Mapping User Guide

**Version:** 0.0.1  
**Date:** 2026-05-03

---

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Mapping Structure](#mapping-structure)
4. [Step-by-Step: Creating Your First Mapping](#step-by-step-creating-your-first-mapping)
5. [Advanced Patterns](#advanced-patterns)
6. [Ontology Requirements](#ontology-requirements)
7. [Common Pitfalls and Gotchas](#common-pitfalls-and-gotchas)
8. [Debugging Tips](#debugging-tips)
9. [Examples](#examples)

---

## Overview

kgraphing's **Schema Mapping** system allows you to convert tabular data (Excel, CSV, pandas DataFrames) into well-formed RDF graphs using declarative JSON configuration files.

Instead of writing Python code to transform data, you describe **what** you want mapped, and kgraphing handles the **how**.

### What Makes This Different?

- **Declarative**: Specify your mappings in JSON, not code
- **Hierarchical**: Built-in support for nested FQN structures (Company → Department → Employee)
- **Validated**: SHACL integration ensures your output conforms to expected patterns
- **Reusable**: Configuration files can be shared and versioned

---

## Core Concepts

### 1. The Mapping File Structure

A mapping configuration has five main components:

```json
{
  "$schema": ".../schemamappingschema.json",
  "Namespaces": { ... },
  "GlobalVariables": { ... },
  "NamedObjects": [ ... ],
  "Relationships": [ ... ],
  "Properties": [ ... ]
}
```

| Component | Purpose |
|-----------|---------|
| `Namespaces` | Define URI shortcuts used in your mappings |
| `GlobalVariables` | Constants available to all mappings |
| `NamedObjects` | Define entities that will be created (people, orgs, documents, etc.) |
| `Relationships` | Define links between entities |
| `Properties` | Define attributes of entities (names, dates, values) |

### 2. NamedObjects vs. Relationships vs. Properties

The mapping language distinguishes between three types of constructs:

| Type | Creates | Example |
|------|---------|---------|
| **NamedObject** | A URI-referring entity | `http://example.org/person/123` |
| **Relationship** | A connection between two entities | `http://example.org/person/123 → worksFor → http://example.org/org/456` |
| **Property** | A connection to a literal value | `http://example.org/person/123 → hasName → "Alice Smith"` |

### 3. The Fully Qualified Name (FQN) System

The **FQN** is the heart of kgraphing's entity resolution. It provides a hierarchical naming system for entities.

#### What is an FQN?

An FQN is a dot-separated string that describes an entity's position in a hierarchy:

```
Company.A department. B department. Sales employee
```

This becomes the FQN: `Company.A.B.Sales`

#### Why Use FQNs?

1. **Unique identification**: The FQN uniquely identifies an entity within your dataset
2. **Hierarchical context**: Encodes parent-child relationships naturally
3. **Cross-reference resolution**: Same FQNs in different datasets can be merged automatically

#### FQN Examples

```
Vocabularies.TestAlphabetVocab.Apple           (single level)
Vocabularies.TestAlphabetVocab.Fruit.Apple      (two levels)
Vocabularies.TestAlphabetVocab.Fruit.Apple.Green (three levels)
```

#### FQN Structure

```
ParentTag.Column → ChildTag.Column → LeafTag.Column
        ↓             ↓              ↓
      (A)           (B)           (Apple)

FQN = "A.B.Apple"
```

### 4. Definition vs. Reference

The `Definition` flag distinguishes where entities are "defined" from where they are merely "referenced":

- **Definition: true** - This entity is fully described in the dataset (has all properties)
- **Definition: false** - This is a reference to an entity (may lack full description)

When kgraphing processes data:
- It first creates all **definition** entities
- Then processes **reference** entities
- If a referenced entity isn't found as a definition, it's flagged as "undefined"

This enables **data lineage** and **quality checking**.

### 5. GlobalVariables

Variables defined once at the top level that are available throughout the mapping:

```json
{
  "GlobalVariables": {
    "default_region": "North America",
    "status_1": "Active",
    "status_0": "Inactive"
  }
}
```

These are particularly useful for values that are constant across all rows but needed in multiple mappings.

---

## Mapping Structure

### The JSON Schema

A valid mapping must conform to the schema defined in `src/kgraphing/jschema/schemamappingschema.json`. The minimum required fields are:

```json
{
  "$schema": "https://raw.githubusercontent.com/yourorg/kgraphing/main/src/kgraphing/jschema/schemamappingschema.json",
  "Namespaces": { "key": "value" },
  "GlobalVariables": { "key": "value" },
  "NamedObjects": [ ... ],
  "Relationships": [ ... ],
  "Properties": [ ... ]
}
```

### Required Fields for Each Section

#### NamedObjects

```json
{
  "TargetClass": "http://example.org#Person",        // The RDF class/type
  "URIBase": "http://example.org/person/",           // Base URI for entity URIs
  "Instances": [
    {
      "InstanceName": "person_mapping",              // Unique identifier for this mapping
      "SubjectTag": "person_id",                     // Column providing entity identifier
      "ParentTag": "department",                     // Column providing parent context
      "Definition": true,                            // true = fully described, false = reference only
      "EnableMultiValues": false                     // true = parse comma-separated lists
    }
  ]
}
```

#### Relationships

```json
{
  "Predicate": "http://xmlns.com/foaf/0.1/member",    // The relationship type
  "Instances": [
    {
      "InstanceName": "person_to_org",
      "SubjectTag": "person_id",                      // Column with subject entity FQN
      "ObjectTag": "organization",                    // Column with object entity FQN
      "EnableMultiValues": false
    }
  ]
}
```

#### Properties

```json
{
  "Predicate": "http://xmlns.com/foaf/0.1/name",      // The property type
  "Instances": [
    {
      "InstanceName": "name_property",
      "SubjectTag": "person_id",                      // Column with subject entity FQN
      "LiteralTag": "full_name",                      // Column with the literal value
      "EnableMultiValues": false
    }
  ]
}
```

---

## Step-by-Step: Creating Your First Mapping

### Example Dataset

Let's say you have this Excel data (`people.xlsx`):

| person_id | department | name          | status |
|-----------|------------|---------------|--------|
| P001      | IT         | Alice Smith   | 1      |
| P002      | IT         | Bob Jones     | 0      |
| P003      | Sales      | Carol White   | 1      |

### Step 1: Define Namespaces

```json
{
  "$schema": "schemamappingschema.json",
  "Namespaces": {
    "foaf": "http://xmlns.com/foaf/0.1/",
    "org": "http://example.org/org/",
    "schema": "http://schema.org/"
  },
```

### Step 2: Define Global Variables

```json
  "GlobalVariables": {
    "status_active": "Active",
    "status_inactive": "Inactive"
  },
```

### Step 3: Define NamedObjects

We have **Person** entities that belong to **Department** entities:

```json
  "NamedObjects": [
    {
      "TargetClass": "http://xmlns.com/foaf/0.1/Person",
      "URIBase": "http://example.org/person/",
      "Instances": [{
        "InstanceName": "person_entity",
        "SubjectTag": "person_id",
        "ParentTag": "department",
        "Definition": true
      }]
    },
    {
      "TargetClass": "http://example.org#Department",
      "URIBase": "http://example.org/dept/",
      "Instances": [{
        "InstanceName": "dept_entity",
        "SubjectTag": "department",
        "ParentTag": null,
        "Definition": true
      }]
    }
  ],
```

### Step 4: Define Properties

The `name` and `status` are properties of the Person:

```json
  "Properties": [
    {
      "Predicate": "http://xmlns.com/foaf/0.1/name",
      "Instances": [{
        "InstanceName": "name_property",
        "SubjectTag": "person_id",
        "LiteralTag": "name"
      }]
    },
    {
      "Predicate": "http://example.org#status",
      "Instances": [{
        "InstanceName": "status_property",
        "SubjectTag": "person_id",
        "LiteralTag": "status"
      }]
    }
  ]
}
```

### Step 5: Test Your Mapping

```python
from kgraphing.ingest import schemamapping
from kgraphing.ingest import kgpipeline
import pandas as pd

# Load the data
df = pd.read_excel("people.xlsx")

# Create the mapping
mapping = schemamapping.SchemaMapping("people_mapping.json")

# Generate RDF graph
graph = mapping.to_rdf_graph(df)

# Output
print(f"Generated {len(graph)} triples")
graph.serialize("people.rdf", format="xml")
```

### Expected Output

```
Defined, References
2 0
rdf_parse:start 2026-05-03 10:30:00
:... set of all FQN parents
Warning - the following FullyQualifiedNames are inferred but not directly referenced in this file: []
Objects, Unique Objects
5 5
rdf_parse:end 2026-05-03 10:30:00
```

---

## Advanced Patterns

### Pattern 1: Multi-Valued Columns

When a column contains comma-separated values (e.g., skills, tags):

```json
{
  "Properties": [{
    "Predicate": "http://example.org#skills",
    "Instances": [{
      "InstanceName": "skills_property",
      "SubjectTag": "person_id",
      "LiteralTag": "skills",
      "EnableMultiValues": true
    }]
  }]
}
```

Input: `skills = "Python, R, SQL"`
Output: Three separate triples, one for each skill.

### Pattern 2: Nested Hierarchy

For deeper hierarchies, chain multiple NamedObjects:

```json
{
  "NamedObjects": [
    {
      "TargetClass": "http://example.org#Company",
      "URIBase": "http://example.org/company/",
      "Instances": [{
        "InstanceName": "company_entity",
        "SubjectTag": "company_id",
        "ParentTag": null,
        "Definition": true
      }]
    },
    {
      "TargetClass": "http://example.org#Department",
      "URIBase": "http://example.org/dept/",
      "Instances": [{
        "InstanceName": "dept_entity",
        "SubjectTag": "department_id",
        "ParentTag": "company_id",
        "Definition": true
      }]
    },
    {
      "TargetClass": "http://example.org#Project",
      "URIBase": "http://example.org/project/",
      "Instances": [{
        "InstanceName": "project_entity",
        "SubjectTag": "project_id",
        "ParentTag": "department_id",
        "Definition": true
      }]
    }
  ]
}
```

Result:
- `Company_id` → parent of nothing (root)
- `Department_id` → parent is `Company_id`
- `Project_id` → parent is `Department_id`

FQN becomes: `Company_ABC.Department_XYZ.Project_123`

### Pattern 3: Cross-Referencing Between Rows

For relationships between entities in different rows:

```json
{
  "Relationships": [{
    "Predicate": "http://xmlns.com/foaf/0.1/member",
    "Instances": [{
      "InstanceName": "membership",
      "SubjectTag": "person_id",
      "ObjectTag": "organization"
    }]
  }]
}
```

| person_id | name     | organization |
|-----------|----------|--------------|
| P001      | Alice    | ACME         |
| P002      | Bob      | ACME         |
| ACME      | (org)    | (none)       |

Result: `http://example.org/person/P001 → foaf:member → http://example.org/org/ACME`

### Pattern 4: Definition vs. Reference

Use this when some entities are fully described in one file but only referenced in another:

```json
{
  "NamedObjects": [
    {
      "TargetClass": "http://example.org#Project",
      "URIBase": "http://example.org/project/",
      "Instances": [
        {
          "InstanceName": "project_definition",
          "SubjectTag": "project_id",
          "ParentTag": null,
          "Definition": true      // Full description available
        },
        {
          "InstanceName": "project_reference",
          "SubjectTag": "ref_project_id",
          "ParentTag": null,
          "Definition": false     // Just a reference
        }
      ]
    }
  ]
}
```

---

## Ontology Requirements

### What is an Ontology in This Context?

An **ontology** is a formal specification of classes, properties, and constraints that your mapped data will conform to. It's your "schema" or "target model".

### Required Ontology Elements

For kgraphing to work, you need an ontology that defines:

1. **TargetClasses** - All the RDF classes referenced in your `NamedObjects`
2. **Predicates** - All the URIs referenced in `Relationships` and `Properties`
3. **Validation Shapes** (optional but recommended) - SHACL files for quality checking

### Example Ontology (kgmeta)

kgraphing ships with a built-in ontology (`kgmeta.owl`) that defines:
- `KGMETA.FullyQualifiedName` - Property for storing FQN
- `KGMETA.Name` - Property for storing entity names
- `KGMETA.SchemaMapping` - Validation shapes for schema mappings

### Creating Your Target Ontology

A minimal target ontology for your domain:

```turtle
@prefix ex: <http://example.org/onto/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Define your classes
ex:Person a rdfs:Class ;
    rdfs:label "Person" ;
    rdfs:comment "A person entity" .

ex:Organization a rdfs:Class ;
    rdfs:label "Organization" ;
    rdfs:comment "An organization entity" .

# Define properties
ex:fullName a rdf:Property ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:string .

ex:memberOf a rdf:Property ;
    rdfs:domain ex:Person ;
    rdfs:range ex:Organization .
```

### Using SHACL Validation

To validate your mapped output, create a SHACL file:

```turtle
@prefix ex: <http://example.org/onto/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

ex:PersonShape a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:fullName ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] .
```

Use in pipeline:

```python
pipeline = kgpipeline.KGraphPipeline(
    mapping_config="people_mapping.json",
    validation_shacl=["people_shape.ttl"]
)
graph = pipeline.process(df)
```

---

## Common Pitfalls and Gotchas

### Pitfall 1: ParentTag Column Doesn't Exist

**Problem:** `ParentTag` references a column that doesn't exist in your data.

**Error message:**
```
TypeError: None is not a valid FQN component
```

**Solution:** Double-check that both `SubjectTag` and `ParentTag` columns exist in your dataset.

### Pitfall 2: Circular Hierarchy References

**Problem:** FQN hierarchy creates a cycle (A's parent is B, B's parent is A).

**Error:** Stack overflow or infinite recursion.

**Solution:** Ensure your ParentTag relationships are acyclic. The hierarchy must flow from leaves to root, never back.

### Pitfall 3: Undefined FQN References

**Problem:** A relationship references an FQN that doesn't exist as a defined entity.

**Error message:**
```
Warning - the following FullyQualifiedNames are inferred but not directly referenced in this file: [...]
```

**Solution:** Either:
1. Add the missing entity as a NamedObject with `Definition: true`
2. Check that the FQN values in your relationship column match exactly (case-sensitive!)

### Pitfall 4: Multi-Values Column Containing Non-Comma Delimiters

**Problem:** Column marked as `EnableMultiValues: true` contains values that aren't comma-separated.

**Error:**
```
split_on_comma_respecting_quotes exception
```

**Solution:** Either:
1. Clean your data first
2. Use `EnableMultiValues: false` and handle manually

### Pitfall 5: Namespace Prefixes Mismatch

**Problem:** The namespace prefix you use in your mapping doesn't match any defined namespace.

**Error:** Graph serialization shows `unknown:` prefix.

**Solution:** Define all prefixes in the `Namespaces` section:

```json
"Namespaces": {
  "foaf": "http://xmlns.com/foaf/0.1/",
  "ex": "http://example.org/"
}
```

### Pitfall 6: FQN Case Sensitivity

**Problem:** FQN values differ in case between definition and reference.

**Example:**
- Defined as: `Company.Sales`
- Referenced as: `Company.sales`

**Result:** They're treated as different entities!

**Solution:** Be consistent. Use a naming convention (e.g., title case) and stick to it.

### Pitfall 7: ParentTag is `null` but Entity Has Parents

**Problem:** Setting `ParentTag: null` when the entity should have a parent.

**Result:** The entity becomes a root-level entity, losing its hierarchical context.

**Solution:** Set `ParentTag` to the actual parent column name, or explicitly accept it as a root entity.

### Pitfall 8: Empty Strings vs. Missing Values

**Problem:** Pandas converts empty cells to `NaN`, but your FQN expects non-empty strings.

**Result:** Entities with empty SubjectTag columns are created with empty FQNs.

**Solution:** Pre-clean your data:

```python
df = df.dropna(subset=['person_id'])
```

### Pitfall 9: Column Names with Spaces or Special Characters

**Problem:** Column names like "Full Name" or "Date Joined" cause issues.

**Result:** Parsing errors in the RDF conversion.

**Solution:** These work but can be fragile. Best practice: rename columns to snake_case before mapping.

### Pitfall 10: Duplicate InstanceNames

**Problem:** Two NamedObjects, Relationships, or Properties use the same `InstanceName`.

**Error:**
```
Duplicate InstanceName detected: person_mapping
```

**Solution:** Each `InstanceName` must be unique across the entire mapping file.

---

## Debugging Tips

### Enable Verbose Output

The mapping system prints progress information:

```
Defined, References
2 0
rdf_parse:start 2026-05-03 10:30:00
:... set of all FQN parents
Warning - the following FullyQualifiedNames are inferred but not directly referenced: []
Objects, Unique Objects
5 5
```

### Inspect the Raw Graph

To debug what's happening:

```python
mapping = schemamapping.SchemaMapping("mapping.json")
graph = mapping.to_rdf_graph(df)

# Print all triples
for s, p, o in graph:
    print(f"{s} -- {p} --> {o}")
```

### Check Entity FQN Index

```python
# After mapping creation
for fqn, obj in mapping.entity_fqn_index.items():
    print(f"{fqn} → {obj.uri}")
```

### Validate JSON Before Running

```python
import json
from kgraphing.declarations import SCHEMAMAPPINGSCHEMA
import jsonschema

with open("mapping.json") as f:
    config = json.load(f)

jsonschema.validate(config, schema=SCHEMAMAPPINGSCHEMA)
print("Mapping JSON is valid!")
```

### Check Column Mapping

```python
mapping = schemamapping.SchemaMapping("mapping.json")
print("Referenced columns:", mapping.referenced_columns)
print("Multi-value columns:", mapping.multivalue_columns)
```

---

## Examples

### Example 1: Simple Person Entity

```json
{
  "$schema": "schemamappingschema.json",
  "Namespaces": {
    "foaf": "http://xmlns.com/foaf/0.1/"
  },
  "GlobalVariables": {},
  "NamedObjects": [{
    "TargetClass": "http://xmlns.com/foaf/0.1/Person",
    "URIBase": "http://example.org/person/",
    "Instances": [{
      "InstanceName": "person",
      "SubjectTag": "id",
      "ParentTag": null,
      "Definition": true
    }]
  }],
  "Properties": [{
    "Predicate": "http://xmlns.com/foaf/0.1/name",
    "Instances": [{
      "InstanceName": "person_name",
      "SubjectTag": "id",
      "LiteralTag": "name"
    }]
  }],
  "Relationships": []
}
```

### Example 2: Organization with Members

```json
{
  "$schema": "schemamappingschema.json",
  "Namespaces": {
    "foaf": "http://xmlns.com/foaf/0.1/",
    "ex": "http://example.org/"
  },
  "GlobalVariables": {},
  "NamedObjects": [
    {
      "TargetClass": "http://example.org/Organization",
      "URIBase": "http://example.org/org/",
      "Instances": [{
        "InstanceName": "org",
        "SubjectTag": "org_id",
        "ParentTag": null,
        "Definition": true
      }]
    }
  ],
  "Properties": [{
    "Predicate": "http://xmlns.com/foaf/name",
    "Instances": [{
      "InstanceName": "org_name",
      "SubjectTag": "org_id",
      "LiteralTag": "org_name_col"
    }]
  }],
  "Relationships": [{
    "Predicate": "http://xmlns.com/foaf/member",
    "Instances": [{
      "InstanceName": "member_rel",
      "SubjectTag": "person_id",
      "ObjectTag": "org_id"
    }]
  }]
}
```

### Example 3: Multi-Level Hierarchy

```json
{
  "$schema": "schemamappingschema.json",
  "Namespaces": {
    "ex": "http://example.org/"
  },
  "GlobalVariables": {},
  "NamedObjects": [
    {
      "TargetClass": "http://example.org#Company",
      "URIBase": "http://example.org/company/",
      "Instances": [{
        "InstanceName": "company",
        "SubjectTag": "company_id",
        "ParentTag": null,
        "Definition": true
      }]
    },
    {
      "TargetClass": "http://example.org#Department",
      "URIBase": "http://example.org/dept/",
      "Instances": [{
        "InstanceName": "department",
        "SubjectTag": "dept_id",
        "ParentTag": "company_id",
        "Definition": true
      }]
    },
    {
      "TargetClass": "http://example.org#Project",
      "URIBase": "http://example.org/project/",
      "Instances": [{
        "InstanceName": "project",
        "SubjectTag": "project_id",
        "ParentTag": "dept_id",
        "Definition": true
      }]
    }
  ],
  "Properties": [],
  "Relationships": []
}
```

---

## Next Steps

1. **Define your ontology** - Ensure all target classes and predicates are defined
2. **Create SHACL shapes** - For validation (optional but recommended)
3. **Start with a simple mapping** - Get one NamedObject working first
4. **Add Relationships and Properties** - Gradually expand the mapping
5. **Test with sample data** - Verify output before processing full datasets
6. **Integrate with KGraphPipeline** - Add validation and name mastering

---

## Appendix: Column Reference Summary

| Field | Description | Required | Example |
|-------|-------------|----------|---------|
| `InstanceName` | Unique identifier for this mapping | Yes | `person_entity` |
| `SubjectTag` | Column providing entity identifier or subject | Yes | `person_id` |
| `ParentTag` | Column providing parent FQN context | No (for NamedObjects) | `department_id` |
| `ObjectTag` | Column providing object entity for relationships | Yes (for Relationships) | `organization_id` |
| `LiteralTag` | Column providing literal value for properties | Yes (for Properties) | `full_name` |
| `TargetClass` | RDF class/URI for the entity | Yes | `http://xmlns.com/foaf/0.1/Person` |
| `Predicate` | RDF property/relationship URI | Yes | `http://xmlns.com/foaf/0.1/name` |
| `URIBase` | Base URI for entity URIs | Yes (NamedObjects) | `http://example.org/person/` |
| `Definition` | true = fully described, false = reference | No (defaults to false) | `true` |
| `EnableMultiValues` | Parse comma-separated lists | No (defaults to false) | `true` |
