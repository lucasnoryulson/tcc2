# Catálogo de vistas diagnósticas v1

Este índice contém rótulos de avaliação e nunca é enviado ao modelo.

| Caso | Família | Partição | Origem | Causa anotada |
|---|---|---|---|---|
| d01 | dot | development | archived_measurement_view | NO_PARALLEL_GAIN |
| d02 | dot | development | archived_measurement_view | NEAR_TIE |
| d03 | dot | development | archived_measurement_view | NO_PARALLEL_GAIN |
| d04 | dot | development | controlled_evidence_omission | INSUFFICIENT_EVIDENCE |
| d05 | dot | development | contract_compatibility_probe | SCHEMA_MISMATCH |
| d06 | dot | development | executed_controlled_compilation_failure | COMPILE_ERROR |
| d07 | dot | development | executed_controlled_compilation_failure | COMPILE_ERROR |
| d08 | dot | development | executed_controlled_semantic_mutation | INCORRECT_RESULT |
| d09 | dot | development | executed_controlled_semantic_mutation | INCORRECT_RESULT |
| d10 | nussinov | development | archived_static_analysis_view | INSUFFICIENT_EVIDENCE |
| d11 | nussinov | development | archived_compiler_diagnostic | VECTORIZATION_BLOCKED |
| d12 | nussinov | development | archived_compiler_diagnostic | VECTORIZATION_COST_MODEL |
| d13 | gemm | heldout | archived_measurement_view | MEASURED_GAIN |
| d14 | gemm | heldout | archived_measurement_view | MEASURED_GAIN |
| d15 | gemm | heldout | controlled_evidence_omission | INSUFFICIENT_EVIDENCE |
| d16 | gemm | heldout | executed_controlled_compilation_failure | COMPILE_ERROR |
| d17 | gemm | heldout | contract_compatibility_probe | SCHEMA_MISMATCH |
| d18 | jacobi | heldout | archived_measurement_view | MEASURED_GAIN |
| d19 | jacobi | heldout | archived_measurement_view | SCALING_REGRESSION |
| d20 | jacobi | heldout | source_derived_annotation | DEPENDENCE_RISK |
| d21 | jacobi | heldout | controlled_evidence_omission | INSUFFICIENT_EVIDENCE |
| d22 | covariance | heldout | archived_measurement_view | MEASURED_GAIN |
| d23 | covariance | heldout | archived_static_analysis_view | INSUFFICIENT_EVIDENCE |
| d24 | covariance | heldout | contract_compatibility_probe | SCHEMA_MISMATCH |

Anotação autoral por rubrica, sem validação humana independente.
Fontes, snapshots, SHA e ações aceitáveis estão em `v1/catalog.json`.
Leia `../../docs/publication/DIAGNOSTIC_PROTOCOL.md` antes de interpretar qualquer taxa.
