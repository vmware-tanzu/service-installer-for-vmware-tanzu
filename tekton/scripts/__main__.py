#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import sys
from pathlib import Path
import click
import yaml
from constants.constants import Paths, Upgrade_Extensions
from model.desired_state import DesiredState
from model.user_credentials import UserCredentials
from model.run_config import RunConfig, DeploymentPlatform
from model.status import State, get_fresh_state
from model.status import Day2DesiredState
from util.env_validation import EnvValidator
from util.file_helper import FileHelper
from util.git_helper import Git
from util.logger_helper import LoggerHelper
from util.tanzu_utils import TanzuUtils
from workflows.ra_alb_workflow import RALBWorkflow
from workflows.ra_mgmt_cluster_workflow import RaMgmtClusterWorkflow
from workflows.ra_shared_cluster_workflow import RaSharedClusterWorkflow
from workflows.ra_workload_cluster_workflow import RaWorkloadClusterWorkflow
from workflows.ra_day2_workflow import RaDay2WorkflowCheck
from workflows.ra_upgrade_workflow import RaUpgradeWorkflow
from workflows.ra_deploy_ext_workflow import RaDeployExtWorkflow
from workflows.ra_resize_workflow import RaResizeWorkflow
from workflows.ra_scale_workflow import RaScaleWorkflow
from pre_setup.pre_setup import PreSetup
from util.cleanup_util import CleanUpUtil
from pre_setup.tkn_docker_img import GenerateTektonDockerImage

logger = LoggerHelper.get_logger(name="__main__")

def load_run_config(root_dir):

    state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
    if not os.path.exists(state_file_path):
        logger.error("state file missing")
        return
    state: State = FileHelper.load_state(state_file_path)
    desired_state: DesiredState = FileHelper.load_desired_state(os.path.join(root_dir,
                                                                             Paths.DESIRED_STATE_PATH))
    day2_config: Day2DesiredState = FileHelper.load_day2_desired_state(os.path.join(root_dir, Paths.DAY2_PATH))
    if root_dir == ".":
        user_cred: UserCredentials = FileHelper.load_values_yaml(os.path.join(root_dir,
                                                                              Paths.VALUES_YAML_PATH.split("/")[1]))
    else:
        user_cred: UserCredentials = FileHelper.load_values_yaml(os.path.join(root_dir, Paths.VALUES_YAML_PATH))
    support_matrix = yaml.safe_load(FileHelper.read_resource(Paths.SUPPORT_MATRIX_FILE))
    run_config = RunConfig(root_dir=root_dir, state=state, desired_state=desired_state,
                           support_matrix=support_matrix,
                           deployment_platform=DeploymentPlatform.VSPHERE,
                           user_cred=user_cred,
                           vmc=None,
                           day2_ops_details=day2_config)
    return run_config

@click.group()
@click.option("--root-dir", default=".tmp")
@click.pass_context
def cli(ctx, root_dir):
    ctx.ensure_object(dict)
    ctx.obj["ROOT_DIR"] = root_dir

    deployment_config_filepath = os.path.join(ctx.obj["ROOT_DIR"], Paths.MASTER_SPEC_PATH)
    # file_linker(json_spec_path, deployment_config_filepath)
    # prevalidation
    if not Path(deployment_config_filepath).is_file():
        logger.warn("Missing config in path: %s", deployment_config_filepath)
    os.makedirs(Paths.TMP_DIR, exist_ok=True)

@cli.group()
@click.pass_context
def tkn_docker(ctx):
    ctx.ensure_object(dict)

@tkn_docker.command(name="build")
@click.pass_context
def build_docker(ctx):

    support_matrix_file_path = os.path.join(ctx.obj["ROOT_DIR"], "scripts", Paths.SUPPORT_MATRIX_FILE)
    gen_dock_obj = GenerateTektonDockerImage(support_matrix_file_path)
    status = gen_dock_obj.generate_tkn_docker_image()
    if not status:
        raise

@cli.group()
@click.pass_context
def avi(ctx):
    ctx.ensure_object(dict)

@avi.command(name="deploy")
@click.pass_context
def avi_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    pre_setup_obj = PreSetup(root_dir=ctx.obj["ROOT_DIR"], run_config=run_config)
    result_dict, msg = pre_setup_obj.pre_check_avi()
    if not result_dict["avi"]["deployed"]:
        logger.warning(msg)
        RALBWorkflow(run_config=run_config).avi_controller_setup()
    elif "AVI Version mis-matched" in msg:
        logger.error(msg)
    elif "UP" not in result_dict["avi"]["health"]:
        logger.error(msg)
        # TODO: Can we start AVI ?
    else:
        logger.info(msg)
        logger.debug(result_dict)

@cli.group()
@click.pass_context
def mgmt(ctx):
    click.echo(f"root dir is {ctx.obj['ROOT_DIR']}")


@mgmt.command(name="deploy")
@click.pass_context
def mgmt_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    pre_setup_obj = PreSetup(root_dir=ctx.obj["ROOT_DIR"], run_config=run_config)
    cleanup_obj = CleanUpUtil()
    result_dict, msg = pre_setup_obj.pre_check_mgmt()
    if not result_dict["mgmt"]["deployed"]:
        logger.warning(msg)
        msg, status = RaMgmtClusterWorkflow(run_config).create_mgmt_cluster()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    elif "UP" not in result_dict["mgmt"]["health"]:
        logger.warning(msg)
        cleanup_obj.delete_mgmt_cluster(result_dict["name"])
        msg, status = RaMgmtClusterWorkflow(run_config).create_mgmt_cluster()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    else:
        logger.info(msg)
        logger.debug(result_dict)

@mgmt.command(name="enable-wcp")
@click.pass_context
def enable_wcp(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    pre_setup_obj = PreSetup(root_dir=ctx.obj["ROOT_DIR"], run_config=run_config)
    result_dict, msg = pre_setup_obj.pre_check_enable_wcp()
    if not result_dict["enable_wcp"]["enabled"]:
        logger.warning(msg)
        msg, status = RaMgmtClusterWorkflow(run_config).enable_wcp()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    elif "UP" not in result_dict["enable_wcp"]["health"]:
        logger.warning(msg)
    else:
        logger.warning(msg)

@cli.group()
@click.pass_context
def shared_services(ctx):
    ctx.ensure_object(dict)

@shared_services.command(name="deploy-cluster")
@click.pass_context
def ss_cluster_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    pre_setup_obj = PreSetup(root_dir=ctx.obj["ROOT_DIR"], run_config=run_config)
    cleanup_obj = CleanUpUtil()
    result_dict, msg = pre_setup_obj.pre_check_shrd()
    if not result_dict["shared_services"]["deployed"]:
        logger.warning(msg)
        msg, status = RaSharedClusterWorkflow(run_config).deploy()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    elif "UP" not in result_dict["shared_services"]["health"]:
        logger.warning(msg)
        cleanup_obj.delete_cluster(result_dict["name"])
        msg, status = RaSharedClusterWorkflow(run_config).deploy()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    else:
        logger.info(msg)
        logger.debug(result_dict)

@cli.group()
@click.pass_context
def workload_clusters(ctx):
    ctx.ensure_object(dict)

@workload_clusters.command(name="deploy")
@click.pass_context
def wl_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    pre_setup_obj = PreSetup(root_dir=ctx.obj["ROOT_DIR"], run_config=run_config)
    cleanup_obj = CleanUpUtil()
    result_dict, msg = pre_setup_obj.pre_check_wrkld()
    if not result_dict["workload_clusters"]["deployed"]:
        logger.warning(msg)
        msg, status = RaWorkloadClusterWorkflow(run_config).deploy()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    elif "UP" not in result_dict["workload_clusters"]["health"]:
        logger.warning(msg)
        cleanup_obj.delete_cluster(result_dict["name"])
        msg, status = RaWorkloadClusterWorkflow(run_config).deploy()
        if status != 200:
            logger.error(msg)
            sys.exit(1)
    else:
        logger.info(msg)
        logger.debug(result_dict)

@workload_clusters.command(name="tkgs-wld-setup")
@click.pass_context
def tkgs_workload(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    msg, status = RaWorkloadClusterWorkflow(run_config).create_workload()
    if status != 200:
            logger.error(msg)
            sys.exit(1)

@workload_clusters.command(name="tkgs-wld-ns-setup")
@click.pass_context
def tkgs_namespace(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    msg, status = RaWorkloadClusterWorkflow(run_config).create_name_space()
    if status != 200:
            logger.error(msg)
            sys.exit(1)

@cli.group()
@click.pass_context
def extns(ctx):
    ctx.ensure_object(dict)

@extns.command(name="deploy")
@click.pass_context
def extns_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaDeployExtWorkflow(run_config).deploy_tkg_extensions()

@extns.command(name="upgrade")
@click.pass_context
def extns_upgrade(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    Upgrade_Extensions.UPGRADE_EXTN = True
    RaDeployExtWorkflow(run_config).deploy_tkg_extensions()

@cli.command(name="validate-day2-ops")
@click.pass_context
def validate_day2_op(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaDay2WorkflowCheck(run_config).validate_day2_ops()

@cli.command(name="execute_update")
@click.pass_context
def execute_update(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaUpgradeWorkflow(run_config).update_workflow()

@cli.command(name="execute_resize")
@click.pass_context
def execute_resize(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaResizeWorkflow(run_config).resize_workflow()

@cli.command(name="execute_scale")
@click.pass_context
def execute_scale(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaScaleWorkflow(run_config).scale_workflow()

@cli.command(name="pull-kubeconfig")
@click.pass_context
def pull_kubeconfig(ctx):
    TanzuUtils(ctx.obj["ROOT_DIR"]).pull_config()

@cli.group(name="validate")
@click.pass_context
def validate(ctx):
    ctx.ensure_object(dict)

@validate.command(name="spec")
@click.pass_context
def validate_spec(ctx):
    root_dir = ctx.obj["ROOT_DIR"]
    state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
    try:
        if not os.path.exists(state_file_path):
            logger.info("No state file present, creating empty state file")
            FileHelper.dump_state(get_fresh_state(), state_file_path)
            Git.add_all_and_commit(os.path.dirname(state_file_path), "Added new state file")
            try:
                FileHelper.clear_kubeconfig(root_dir)
                Git.add_all_and_commit(os.path.join(root_dir, Paths.KUBECONFIG_REPO), "cleanup kubeconfigs")
            except Exception as ex:
                logger.error(str(ex))
    except (FileNotFoundError, IOError, OSError):
        logger.error("Invalid state file, content:%s", FileHelper.read_file(state_file_path))
        return
        # logger.info("pushing fresh spec file")
        # FileHelper.dump_state(get_fresh_state(), state_file_path)
        # Git.add_all_and_commit(os.path.dirname(state_file_path), "Update valid state file")

    state: State = FileHelper.load_state(state_file_path)
    desired_state: DesiredState = FileHelper.load_desired_state(os.path.join(root_dir,
                                                                             Paths.DESIRED_STATE_PATH))

    # logger.debug("spec: \n%s", FileHelper.yaml_from_model(spec))
    logger.debug("***state*** \n%s", FileHelper.yaml_from_model(state))
    logger.debug("***desired_state*** \n%s", FileHelper.yaml_from_model(desired_state))

    logger.info("Validated Spec, State, Desired state")

@cli.command(name="prepare-env")
@click.pass_context
def validate(ctx):
    root_dir = ctx.obj["ROOT_DIR"]
    EnvValidator(root_dir).prepare_env()


if __name__ == "__main__":
    cli(obj={})
