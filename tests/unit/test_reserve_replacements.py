"""Testes unitarios para substituicao por videos reserva e rebalanceamento de sobreposicao."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import gerar_atribuicoes
from tokstance.backend.domain.models import (
    COLUNAS_ERRO,
    COLUNAS_RESULTADO,
    carregar_videos,
)
from tokstance.backend.domain.replacements import (
    aplicar_substituicoes_reserva,
    carregar_atribuicoes,
    garantir_esquema_resultados,
    ler_erros_atribuicoes,
    ler_resultados,
)


def _write_error_rows(errors_file, rows: list[dict[str, str]]) -> None:
    pd.DataFrame(rows, columns=list(COLUNAS_ERRO)).to_csv(errors_file, index=False)


@pytest.mark.unit
def test_apply_reserve_replacements_replaces_individual_video_with_compatible_target_reserve(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    failing_row = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    persisted_errors = ler_erros_atribuicoes(study_paths.arquivo_erros)

    assert persisted_errors.loc[0, "replacement_video_id"] == "7900000000000000001"
    assert persisted_errors.loc[0, "replacement_status"] == "SUBSTITUIDO_OVERLAP"
    assert "7900000000000000001" in set(
        updated[updated["labeler"] == "alice"]["video_id"]
    )


@pytest.mark.unit
def test_apply_reserve_replacements_does_not_reuse_consumed_reserve_across_distinct_failures(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    first_clima = assignments[assignments["video_id"] == "7100000000000000001"].iloc[0]
    second_clima = assignments[assignments["video_id"] == "7100000000000000002"].iloc[0]
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(first_clima["video_id"]),
                "url": str(first_clima["url"]),
                "labeler": str(first_clima["labeler"]),
                "assignment_id": str(first_clima["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "video_id": str(second_clima["video_id"]),
                "url": str(second_clima["url"]),
                "labeler": str(second_clima["labeler"]),
                "assignment_id": str(second_clima["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            },
        ],
    )

    aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    persisted_errors = ler_erros_atribuicoes(study_paths.arquivo_erros)

    assert persisted_errors.loc[0, "replacement_video_id"] == "7900000000000000001"
    assert persisted_errors.loc[1, "replacement_video_id"] == ""
    assert persisted_errors.loc[1, "replacement_status"] == "SEM_RESERVA_COMPATIVEL"


@pytest.mark.unit
def test_apply_reserve_replacements_records_sem_reserva_compativel_when_target_not_in_reserves(
    study_paths,
) -> None:
    pd.DataFrame(
        [
            {
                "id": "7900000000000000099",
                "url": "https://www.tiktok.com/@reserve/video/7900000000000000099",
                "target": "Esportes",
            }
        ]
    ).to_csv(study_paths.arquivo_videos_reserva, index=False)
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice"], "percentual_sobreposicao": 0.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    failing_row = assignments.iloc[0]
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    persisted_errors = ler_erros_atribuicoes(study_paths.arquivo_erros)

    assert persisted_errors.loc[0, "replacement_status"] == "SEM_RESERVA_COMPATIVEL"


@pytest.mark.unit
def test_apply_reserve_replacements_records_sem_reserva_disponivel_when_all_reserves_are_exhausted(
    study_paths,
) -> None:
    pd.DataFrame(
        [
            {
                "id": "7100000000000000001",
                "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
                "target": "Clima",
            }
        ]
    ).to_csv(study_paths.arquivo_videos_reserva, index=False)
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice"], "percentual_sobreposicao": 0.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    failing_row = assignments.iloc[0]
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    persisted_errors = ler_erros_atribuicoes(study_paths.arquivo_erros)

    assert persisted_errors.loc[0, "replacement_status"] == "SEM_RESERVA_DISPONIVEL"


@pytest.mark.unit
def test_apply_reserve_replacements_shares_single_reserve_across_unannotated_overlap_group(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 100.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    alice_row = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(alice_row["video_id"]),
                "url": str(alice_row["url"]),
                "labeler": "alice",
                "assignment_id": str(alice_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    alice_videos = set(updated[updated["labeler"] == "alice"]["video_id"])
    bob_videos = set(updated[updated["labeler"] == "bob"]["video_id"])

    assert "7900000000000000001" in alice_videos
    assert "7900000000000000001" in bob_videos
    assert "7100000000000000001" not in alice_videos
    assert "7100000000000000001" not in bob_videos


@pytest.mark.unit
def test_apply_reserve_replacements_promotes_completed_individual_video_when_overlap_partially_annotated(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    alice_overlap = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_overlap = assignments[
        (assignments["labeler"] == "bob")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    alice_individual = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000002")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_overlap["video_id"]),
                "url": str(alice_overlap["url"]),
                "target": str(alice_overlap["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "21.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_overlap["assignment_id"]),
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "labeler": "alice",
                "video_id": str(alice_individual["video_id"]),
                "url": str(alice_individual["url"]),
                "target": str(alice_individual["target"]),
                "stance": "A Favor",
                "tempo_analise_segundos": "28.0",
                "video_duration": "30.0",
                "assignment_id": str(alice_individual["assignment_id"]),
            },
        ],
        columns=list(COLUNAS_RESULTADO),
    ).to_csv(study_paths.arquivo_resultados, index=False)
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_overlap["video_id"]),
                "url": str(bob_overlap["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_overlap["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    persisted_errors = ler_erros_atribuicoes(study_paths.arquivo_erros)

    assert (
        persisted_errors.loc[0, "replacement_status"]
        == "SUBSTITUIDO_OVERLAP_REBALANCEADO"
    )
    assert persisted_errors.loc[0, "replacement_video_id"] == "7100000000000000002"
    assert "7100000000000000002" in set(updated[updated["labeler"] == "bob"]["video_id"])


@pytest.mark.unit
def test_apply_reserve_replacements_propagates_promoted_video_to_all_pending_group_members(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob", "carol"], "percentual_sobreposicao": 50.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    alice_overlap = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_overlap = assignments[
        (assignments["labeler"] == "bob")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    alice_individual = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000002")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_overlap["video_id"]),
                "url": str(alice_overlap["url"]),
                "target": str(alice_overlap["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "21.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_overlap["assignment_id"]),
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "labeler": "alice",
                "video_id": str(alice_individual["video_id"]),
                "url": str(alice_individual["url"]),
                "target": str(alice_individual["target"]),
                "stance": "Neutro",
                "tempo_analise_segundos": "25.0",
                "video_duration": "30.0",
                "assignment_id": str(alice_individual["assignment_id"]),
            },
        ],
        columns=list(COLUNAS_RESULTADO),
    ).to_csv(study_paths.arquivo_resultados, index=False)
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_overlap["video_id"]),
                "url": str(bob_overlap["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_overlap["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    carol_videos = set(updated[updated["labeler"] == "carol"]["video_id"])

    assert "7100000000000000002" in carol_videos
    assert "7100000000000000001" not in carol_videos


@pytest.mark.unit
def test_apply_reserve_replacements_emits_critico_overlap_inconsistente_when_no_promotion_candidate_exists(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 100.0}
    assignments = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    alice_overlap = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_overlap = assignments[
        (assignments["labeler"] == "bob")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_overlap["video_id"]),
                "url": str(alice_overlap["url"]),
                "target": str(alice_overlap["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "22.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_overlap["assignment_id"]),
            }
        ],
        columns=list(COLUNAS_RESULTADO),
    ).to_csv(study_paths.arquivo_resultados, index=False)
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_overlap["video_id"]),
                "url": str(bob_overlap["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_overlap["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = aplicar_substituicoes_reserva(
        assignments, diretorio_dados=study_paths.diretorio_base
    )
    persisted_errors = ler_erros_atribuicoes(study_paths.arquivo_erros)

    assert (
        persisted_errors.loc[0, "replacement_status"] == "CRITICO_OVERLAP_INCONSISTENTE"
    )
    assert "7100000000000000001" in set(
        updated[updated["labeler"] == "alice"]["video_id"]
    )
    assert "7900000000000000001" in set(updated[updated["labeler"] == "bob"]["video_id"])


@pytest.mark.unit
def test_load_assignments_reuses_persisted_assignments_when_version_matches(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}
    initial = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=study_paths.arquivo_atribuicoes,
    )
    failing_row = initial[
        (initial["labeler"] == "alice")
        & (initial["video_id"] == "7100000000000000001")
    ].iloc[0]
    _write_error_rows(
        study_paths.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    loaded = carregar_atribuicoes(
        config, videos, diretorio_dados=study_paths.diretorio_base
    )

    assert "7900000000000000001" in set(loaded["video_id"])


@pytest.mark.unit
def test_ensure_results_schema_backfills_missing_video_duration_and_legacy_assignment_id(
    study_paths,
) -> None:
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": "7100000000000000001",
                "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
                "target": "Clima",
                "stance": "Contra",
                "tempo_analise_segundos": "20.0",
            }
        ]
    ).to_csv(study_paths.arquivo_resultados, index=False)

    garantir_esquema_resultados(diretorio_dados=study_paths.diretorio_base)
    migrated = ler_resultados(study_paths.arquivo_resultados)

    assert migrated.loc[0, "video_duration"] == "25.0"
    assert migrated.loc[0, "assignment_id"] == "legacy:alice:7100000000000000001"
