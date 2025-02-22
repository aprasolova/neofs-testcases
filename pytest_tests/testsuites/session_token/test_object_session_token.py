import random

import allure
import pytest
from common import COMPLEX_OBJ_SIZE, NEOFS_NETMAP_DICT, SIMPLE_OBJ_SIZE, WALLET_PASS
from file_helper import generate_file
from grpc_responses import SESSION_NOT_FOUND
from neofs_testlib.shell import Shell
from neofs_testlib.utils.wallet import get_last_address_from_wallet
from python_keywords.container import create_container
from python_keywords.neofs_verbs import delete_object, put_object
from python_keywords.session_token import create_session_token


@allure.title("Test Object Operations with Session Token")
@pytest.mark.session_token
@pytest.mark.parametrize(
    "object_size",
    [SIMPLE_OBJ_SIZE, COMPLEX_OBJ_SIZE],
    ids=["simple object", "complex object"],
)
def test_object_session_token(prepare_wallet_and_deposit, client_shell: Shell, object_size):
    """
    Test how operations over objects are executed with a session token

    Steps:
    1. Create a private container
    2. Obj operation requests to the node which IS NOT in the container but granted
        with a session token
    3. Obj operation requests to the node which IS in the container and NOT granted
        with a session token
    4. Obj operation requests to the node which IS NOT in the container and NOT granted
        with a session token
    """

    with allure.step("Init wallet"):
        wallet = prepare_wallet_and_deposit
        address = get_last_address_from_wallet(wallet, "")

    with allure.step("Nodes Settlements"):
        (
            session_token_node_name,
            container_node_name,
            noncontainer_node_name,
        ) = random.sample(list(NEOFS_NETMAP_DICT.keys()), 3)
        session_token_node = NEOFS_NETMAP_DICT[session_token_node_name]["rpc"]
        container_node = NEOFS_NETMAP_DICT[container_node_name]["rpc"]
        noncontainer_node = NEOFS_NETMAP_DICT[noncontainer_node_name]["rpc"]

    with allure.step("Create Session Token"):
        session_token = create_session_token(
            shell=client_shell,
            owner=address,
            wallet_path=wallet,
            wallet_password=WALLET_PASS,
            rpc_endpoint=session_token_node,
        )

    with allure.step("Create Private Container"):
        un_locode = NEOFS_NETMAP_DICT[container_node_name]["UN-LOCODE"]
        locode = "SPB" if un_locode == "RU LED" else un_locode.split()[1]
        placement_policy = (
            f"REP 1 IN LOC_{locode}_PLACE CBF 1 SELECT 1 FROM LOC_{locode} "
            f'AS LOC_{locode}_PLACE FILTER "UN-LOCODE" '
            f'EQ "{un_locode}" AS LOC_{locode}'
        )
        cid = create_container(wallet, shell=client_shell, rule=placement_policy)

    with allure.step("Put Objects"):
        file_path = generate_file(object_size)
        oid = put_object(wallet=wallet, path=file_path, cid=cid, shell=client_shell)
        oid_delete = put_object(wallet=wallet, path=file_path, cid=cid, shell=client_shell)

    with allure.step("Node not in container but granted a session token"):
        put_object(
            wallet=wallet,
            path=file_path,
            cid=cid,
            shell=client_shell,
            endpoint=session_token_node,
            session=session_token,
        )
        delete_object(
            wallet=wallet,
            cid=cid,
            oid=oid_delete,
            shell=client_shell,
            endpoint=session_token_node,
            session=session_token,
        )

    with allure.step("Node in container and not granted a session token"):
        with pytest.raises(Exception, match=SESSION_NOT_FOUND):
            put_object(
                wallet=wallet,
                path=file_path,
                cid=cid,
                shell=client_shell,
                endpoint=container_node,
                session=session_token,
            )
        with pytest.raises(Exception, match=SESSION_NOT_FOUND):
            delete_object(
                wallet=wallet,
                cid=cid,
                oid=oid,
                shell=client_shell,
                endpoint=container_node,
                session=session_token,
            )

    with allure.step("Node not in container and not granted a session token"):
        with pytest.raises(Exception, match=SESSION_NOT_FOUND):
            put_object(
                wallet=wallet,
                path=file_path,
                cid=cid,
                shell=client_shell,
                endpoint=noncontainer_node,
                session=session_token,
            )
        with pytest.raises(Exception, match=SESSION_NOT_FOUND):
            delete_object(
                wallet=wallet,
                cid=cid,
                oid=oid,
                shell=client_shell,
                endpoint=noncontainer_node,
                session=session_token,
            )
