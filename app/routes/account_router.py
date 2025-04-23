# app/routes/account_router.py

from fastapi import APIRouter, Body, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import List, Dict, Any
from beanie import PydanticObjectId
import logging

from app.models.account_model import (
    Account,
    AccountCreate,
    AccountUpdate,
    AccountRead,
)
from app.utilities.utils import apply_and_save

router = APIRouter()


@router.post(
    "/",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(raw: dict = Body(...)) -> Any:
    logging.info("CREATE Account payload: %r", raw)

    # 1) Validate input against AccountCreate
    try:
        payload = AccountCreate(**raw)
    except ValidationError as ve:
        logging.error("Validation error creating Account: %s", ve.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(ve.errors())},
        )

    # 2) Instantiate blank Account (createdAt & updatedAt set by default_factory)
    doc = Account(**payload.dict(exclude_unset=False))

    # 3) Apply payload fields and save (will bump updatedAt)
    try:
        doc = await apply_and_save(doc, payload, exclude_unset=False)
        logging.info("Account created _id=%s", doc.id)
    except Exception as e:
        logging.exception("Error inserting Account")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )

    return doc


@router.get(
    "/",
    response_model=List[AccountRead],
)
async def get_all_accounts() -> Any:
    logging.info("FETCH ALL Accounts")
    try:
        docs = await Account.find_all().to_list()
        logging.info("Fetched %d accounts", len(docs))
        return docs
    except Exception as e:
        logging.exception("Error fetching all Accounts")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get(
    "/{item_id}",
    response_model=AccountRead,
)
async def get_account(item_id: str) -> Any:
    logging.info("FETCH Account %s", item_id)
    try:
        doc = await Account.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning("Account %s not found", item_id)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"Account {item_id} not found"},
            )
        return doc
    except Exception as e:
        logging.exception("Error fetching Account %s", item_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.put(
    "/{item_id}",
    response_model=AccountRead,
)
async def update_account(item_id: str, raw: dict = Body(...)) -> Any:
    logging.info("UPDATE Account %s payload: %r", item_id, raw)

    # 1) Validate input against AccountUpdate
    try:
        payload = AccountUpdate(**raw)
    except ValidationError as ve:
        logging.error("Validation error updating Account: %s", ve.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(ve.errors())},
        )

    # 2) Fetch existing document
    try:
        doc = await Account.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning("Account %s not found for update", item_id)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"Account {item_id} not found"},
            )
    except Exception as e:
        logging.exception("Error retrieving Account %s", item_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )

    # 3) Apply payload fields and save
    try:
        doc = await apply_and_save(doc, payload)
        logging.info("Account %s updated successfully", item_id)
    except Exception as e:
        logging.exception("Error saving updated Account %s", item_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )

    return doc


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_account(item_id: str) -> Any:
    logging.info("DELETE Account %s", item_id)
    try:
        doc = await Account.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning("Account %s not found for deletion", item_id)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"Account {item_id} not found"},
            )
        await doc.delete()
        logging.info("Account %s deleted", item_id)
        return {"detail": "Account deleted successfully"}
    except Exception as e:
        logging.exception("Error deleting Account %s", item_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get(
    "/metadata",
    response_model=Dict[str, Any],
)
async def get_account_metadata() -> Any:
    logging.info("FETCH Account metadata")
    try:
        return Account.get_metadata()
    except Exception as e:
        logging.exception("Error fetching metadata")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
