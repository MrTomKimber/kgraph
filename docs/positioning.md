# kgraphing - Positioning Document

**Date:** 2026-05-03  
**Version:** 0.0.1 (in development)

---

## Executive Summary

kgraphing is a Python library for working with RDF knowledge graphs. It specializes in:

- **Schema-mapping-based ingestion** - Convert tabular data to RDF via JSON configuration
- **URI normalization** - Persistent entity mastery across datasets
- **Ontology auto-resolution** - Discover and cache external ontologies automatically
- **Integrated validation** - SHACL validation as part of the ingestion pipeline

The library sits between **low-end RDF converters** (no validation) and **enterprise RDF platforms** (GraphDB, Virtuoso). Its core value is helping teams convert structured data into **valid, canonical, self-contained knowledge graphs**.

---

## Target Audience

### Primary Users
- **Data Curation Teams** converting spreadsheets/CSVs to RDF for publication
- **Knowledge Engineers** building RDF datasets with consistent URI schemes
- **Research Teams** needing reproducible, offline-capable graph pipelines
- **RDF-onboarding Projects** requiring low-barrier entry to RDF workflows

### Who Should Use kgraphing
- You have tabular data you need to convert to RDF
- URI consistency across datasets matters to you
- You want validation without writing SPARQL
- You work with ontologies that may not match expected URIs
- You need reproducible, scriptable pipelines

### Who Should NOT Use kgraphing
- You need a GUI or web interface
- You want to run SPARQL queries as your primary workflow
- You need distributed/cluster processing
- You're looking for a full-blown triplestore

---

## Core Differentiators

### 1. Schema Mapping Configuration (Primary USP)

Most RDF tools require **code** for data transformations. kgraphing uses **declarative JSON configuration**:

```json
{
  "GlobalVariables": {"prefix": "http://example.org/"},
  "NamedObjects": [{
    "TargetClass": "http://example.org#Person",
    "Instances": [{
      "InstanceName": "person_entity",
      "SubjectTag": "name",
      "ParentTag": "department"
    }]
  }]
}
```

**Why this matters:**
- Non-technical users can configure transformations via JSON
- FQN hierarchy support (nested object structures like `Company.Department.Employee`)
- No Python coding required for common patterns
- Reusable configuration templates

### 2. NameMaster URI Normalization (Secondary USP)

The **NameMaster** class provides persistent URI normalization across datasets:

- Learns canonical URIs for entities
- Remasters incoming graphs to use consistent URIs
- Persists to SQLite between sessions

**Value:** Multiple datasets referencing the same real-world entities converge to consistent URIs automatically.

### 3. OntologyCache Auto-Resolution (Tertiary USP)

The **OntologyCache** iteratively:
- Infers required ontologies from graph content
- Fetches from discovered URIs
- Caches locally for offline work
- Handles URI ≠ file location mapping

**Value:** Works even when your data references ontologies you don't know about in advance.

### 4. Integrated Validation Pipeline

The **KGraphPipeline** combines all steps:

```python
pipeline = KGraphPipeline(
    mapping_config="/path/to/schema_mapping.json",
    validation_shacl=["/path/to/shape.ttl"]
)
graph = pipeline.process(dataframe)  # Validation happens automatically
```

**Value:** Single call from raw data to validated RDF.

---

## Competitive Landscape

### Direct Competitors

| Library | Focus | kgraphing Advantage |
|---------|-----|----|
| **rdflib** | Core RDF manipulation | kgraphing is a pipeline/toolkit on top of rdflib |
| **pyshacl** | SHACL validation | kgraphing integrates pyshacl with ingestion |
| **pandas2rdf** | Simple DataFrame → RDF | kgraphing has schema mapping + validation |
| **kgx (KnowWeaver)** | Multi-format KG transformation | kgraphing focuses on RDF + URI normalization |

### Adjacent Tools

| Library | Focus | Relationship |
|---------|-----|-------------|
| **SPARQLWrapper** | Query clients | Complementary - kgraphing doesn't replace query needs |
| **graphistry** | Graph visualization | kgraphing integrates with NetworkX; graphistry for enterprise viz |
| **pronto** | OWL parsing | Complementary - kgraphing uses rdflib for parsing |

### Positioning Matrix

```
HIGH END:  [Enterprise RDF Platforms]
            (GraphDB, Virtuoso, Blazegraph)
                    |
                    |
MID-TIER:  [kgraphing]
            - Schema mapping
            - URI normalization
            - Validation pipelines
                    |
                    |
LOW END:   [Simple RDF Converters]
            (rdflib-only scripts, basic converters)
```

kgraphing is **not** a triplestore, **not** a SPARQL client, **not** a GUI tool. It's a **transformation and validation layer**.

---

## Feature Comparison

| Feature | kgraphing | rdflib-only | kgx | GraphDB |
|---------|-----------|-------------|-----|-----|
| Tabular → RDF | JSON config | Python code | Python code | SPARQL UPDATE |
| URI normalization | Automatic | Manual | Basic | Manual |
| Schema validation | SHACL integration | Manual | Optional | Built-in |
| Ontology resolution | Auto-discover | Manual | Manual | Manual |
| Storage | SQLite/ memory | In-memory | Various | Triplestore |
| Visualization | Basic NetworkX | None | Basic | Via query |
| Learning curve | Moderate | Low-Moderate | Moderate | High |

---

## Recommended Focus Areas

### Double Down On
1. **Schema mapping documentation** - Make the JSON configuration intuitive with examples
2. **URI normalization demo** - Show multi-dataset convergence clearly
3. **OntologyCache formalization** - Complete the structured registration system

### Consider De-scoping
1. **gvis visualization** - Too basic; better to integrate with existing viz tools
2. **KGStore storage** - Competing tools handle triplestores better; consider this optional

---

## Success Metrics

To validate this positioning:

1. **Adoption by data curation teams** - Are they using it for spreadsheet→RDF workflows?
2. **URI normalization impact** - Does NameMaster solve real pain points?
3. **Ontology resolution adoption** - Does the auto-resolution workflow save time?
4. **Validation as differentiator** - Do users choose kgraphing because of SHACL integration?

---

## Brand Narrative

> "kgraphing makes RDF data quality and consistency tractable.
>
> Instead of wrestling with mismatched URIs, manual validation, and
> opaque transformations, you get:
>
> - **Schema mapping** that anyone can configure
> - **URI normalization** that converges your datasets
> - **Ontology resolution** that works even when you don't know the URIs
> - **Validation** that runs automatically
>
> From spreadsheet to validated RDF graph, in one pipeline."

---

## Next Steps for Positioning Validation

1. Create **comparison page** vs. kgx and simple rdflib scripts
2. Write **schema mapping tutorial** showing non-technical user workflow
3. Build **URI normalization demo** with before/after dataset convergence
4. Gather **user feedback** on whether these differentiators resonate

---

## Appendix: Library Architecture

```
kgraphing/
├── ingest/               # Core value: data → RDF transformation
│   ├── schemamapping.py # JSON config engine (USP #1)
│   ├── kgpipeline.py    # Pipeline orchestration (USP #4)
│   └── namemaster.py    # URI normalization (USP #2)
│
├── rdf2dict.py           # Entity-level analysis (emerging USP)
├── rdfexplorer.py        # Graph introspection
├── store/                # Named graph management
├── ontologies/           # Builtin ontologies (USP #3 support)
├── shapes/               # SHACL shapes
└── gvis.py               # Visualization helpers
```
