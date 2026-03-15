from fastapi import APIRouter
from pydantic import BaseModel

from app.core.schemas import create_data_response
from app.rule_engine.engine import ILRMF_RULES, RuleModuleEnum, get_all_rules, get_rules_by_module

router = APIRouter(prefix="/rules", tags=["Rules"])


class RuleResponse(BaseModel):
    code: str
    name: str
    module: str
    description: str
    statutory_reference: str
    max_score: int


class ModuleResponse(BaseModel):
    id: str
    name: str
    description: str | None
    rule_count: int


@router.get("")
async def list_rules():
    rules = get_all_rules()
    return create_data_response(
        data=[
            RuleResponse(
                code=r.code,
                name=r.name,
                module=r.module.value,
                description=r.description,
                statutory_reference=r.statutory_reference,
                max_score=r.max_score,
            )
            for r in rules
        ]
    )


@router.get("/modules")
async def list_modules():
    modules = []
    for module in RuleModuleEnum:
        rules_in_module = get_rules_by_module(module)
        modules.append(
            ModuleResponse(
                id=module.value,
                name=module.value.replace("_", " ").title(),
                description=f"Contains {len(rules_in_module)} rules",
                rule_count=len(rules_in_module),
            )
        )
    return create_data_response(data=modules)


@router.get("/module/{module_id}")
async def get_module_rules(module_id: str):
    try:
        module = RuleModuleEnum(module_id)
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Module not found")

    rules = get_rules_by_module(module)
    return create_data_response(
        data=[
            RuleResponse(
                code=r.code,
                name=r.name,
                module=r.module.value,
                description=r.description,
                statutory_reference=r.statutory_reference,
                max_score=r.max_score,
            )
            for r in rules
        ]
    )


@router.get("/{rule_code}")
async def get_rule(rule_code: str):
    for rule in ILRMF_RULES:
        if rule.code == rule_code:
            return create_data_response(
                data=RuleResponse(
                    code=rule.code,
                    name=rule.name,
                    module=rule.module.value,
                    description=rule.description,
                    statutory_reference=rule.statutory_reference,
                    max_score=rule.max_score,
                )
            )

    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Rule not found")
