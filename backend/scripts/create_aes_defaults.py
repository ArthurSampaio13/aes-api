import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from src.infrastructure.database.session import local_session  # noqa: E402
from src.infrastructure.database.tenancy import set_tenant_context  # noqa: E402
from src.modules.aes.models.rubric import PromptTemplate, Rubric  # noqa: E402
from src.modules.municipio.models import Municipio  # noqa: E402

DEFAULT_MUNICIPIO = "Município de Demonstração"

DEFAULT_CRITERIA = {
    "adequacao_tema": {"descricao": "Adequação ao tema proposto", "peso": 0.2, "escala_max": 10},
    "estrutura_textual": {"descricao": "Estrutura do gênero textual", "peso": 0.2, "escala_max": 10},
    "coesao_coerencia": {"descricao": "Coesão e coerência entre as ideias", "peso": 0.2, "escala_max": 10},
    "adequacao_ling": {"descricao": "Adequação linguística à norma escrita", "peso": 0.2, "escala_max": 10},
    "vocabulario": {"descricao": "Repertório e precisão vocabular", "peso": 0.2, "escala_max": 10},
}

DEFAULT_PROMPT = (
    "Você auxilia professores do Ensino Fundamental na correção de redações. "
    "Avalie o texto do estudante segundo a rubrica fornecida, atribuindo nota e justificativa por critério, "
    "um feedback geral construtivo e uma sugestão acionável de melhoria. "
    "Baseie toda justificativa em evidências presentes no próprio texto. "
    "Use linguagem clara e apropriada à faixa etária. Não invente trechos que não estejam no texto."
)


async def create_aes_defaults(db: AsyncSession) -> tuple[Municipio, Rubric, PromptTemplate]:
    """Create the demo tenant and the platform-default rubric and prompt template, once."""
    await set_tenant_context(db, None, is_superuser=True)
    municipio = (await db.execute(select(Municipio).where(Municipio.nome == DEFAULT_MUNICIPIO))).scalar_one_or_none()
    if municipio is None:
        municipio = Municipio(nome=DEFAULT_MUNICIPIO)
        db.add(municipio)
        logger.info(f"created municipio {DEFAULT_MUNICIPIO}")

    rubric = (await db.execute(select(Rubric).where(Rubric.municipio_id.is_(None)))).scalars().first()
    if rubric is None:
        rubric = Rubric(municipio_id=None, version=1, criteria=DEFAULT_CRITERIA)
        db.add(rubric)
        logger.info("created platform-default rubric v1")

    template = (await db.execute(select(PromptTemplate).where(PromptTemplate.municipio_id.is_(None)))).scalars().first()
    if template is None:
        template = PromptTemplate(municipio_id=None, version=1, template_text=DEFAULT_PROMPT)
        db.add(template)
        logger.info("created platform-default prompt template v1")

    await db.commit()
    await set_tenant_context(db, None, is_superuser=True)
    await db.refresh(municipio)
    await db.refresh(rubric)
    await db.refresh(template)
    return municipio, rubric, template


async def main() -> None:
    async with local_session() as session:
        await create_aes_defaults(session)


if __name__ == "__main__":
    asyncio.run(main())
