#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
import click
import yaml
from constants.constants import Paths
from model.desired_state import DesiredState
from model.run_config import RunConfig, DeploymentPlatform
from model.status import State, get_fresh_state
from util.env_validation import EnvValidator
from util.file_helper import FileHelper
from util.git_helper import Git
from util.logger_helper import LoggerHelper
from util.tanzu_utils import TanzuUtils
from workflows.ra_alb_workflow import RALBWorkflow
from workflows.ra_mgmt_cluster_workflow import RaMgmtClusterWorkflow
from workflows.ra_shared_cluster_workflow import RaSharedClusterWorkflow
from workflows.ra_mgmt_upgrade_workflow import RaMgmtUpgradeWorkflow
from workflows.ra_shared_cluster_upgrade import RaSharedUpgradeWorkflow
from workflows.ra_workload_cluster_workflow import RaWorkloadClusterWorkflow
from workflows.ra_workload_cluster_upgrade import RaWorkloadUpgradeWorkflow

logger = LoggerHelper.get_logger(name="__main__")

def load_run_config(root_dir):
    # spec: MasterSpec = FileHelper.load_spec(os.path.join(root_dir, Paths.MASTER_SPEC_PATH))
    state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
    if not os.path.exists(state_file_path):
        logger.error("state file missing")
        return
    state: State = FileHelper.load_state(state_file_path)
    desired_state: DesiredState = FileHelper.load_desired_state(os.path.join(root_dir, Paths.DESIRED_STATE_PATH))
    support_matrix = yaml.safe_load(FileHelper.read_resource(Paths.SUPPORT_MATRIX_FILE))
    run_config = RunConfig(root_dir=root_dir, state=state, desired_state=desired_state,
                           support_matrix=support_matrix, deployment_platform=DeploymentPlatform.VSPHERE, vmc=None)

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
def avi(ctx):
    ctx.ensure_object(dict)


@avi.command(name="deploy")
@click.pass_context
def avi_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RALBWorkflow(run_config=run_config).avi_controller_setup()

@cli.group()
@click.pass_context
def mgmt(ctx):
    click.echo(f"root dir is {ctx.obj['ROOT_DIR']}")


@mgmt.command(name="deploy")
@click.pass_context
def mgmt_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaMgmtClusterWorkflow(run_config).create_mgmt_cluster()


@mgmt.command(name="upgrade")
@click.pass_context
def mgmt_upgrade(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaMgmtUpgradeWorkflow(run_config).upgrade_workflow()


@cli.group()
@click.pass_context
def shared_services(ctx):
    ctx.ensure_object(dict)


@shared_services.command(name="deploy-cluster")
@click.pass_context
def ss_cluster_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaSharedClusterWorkflow(run_config).deploy()

@shared_services.command(name="upgrade")
@click.pass_context
def ss_cluster_upgrade(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaSharedUpgradeWorkflow(run_config).upgrade_workflow()

@cli.group()
@click.pass_context
def workload_clusters(ctx):
    ctx.ensure_object(dict)


@workload_clusters.command(name="deploy")
@click.pass_context
def wl_deploy(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaWorkloadClusterWorkflow(run_config).deploy()


@workload_clusters.command(name="upgrade")
@click.pass_context
def wl_upgrade(ctx):
    run_config = load_run_config(ctx.obj["ROOT_DIR"])
    RaWorkloadUpgradeWorkflow(run_config).upgrade_workflow()


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


@validate.command(name="env")
@click.pass_context
def validate_env(ctx):
    root_dir = ctx.obj["ROOT_DIR"]
    EnvValidator(root_dir).validate_all()


@cli.command(name="prepare-env")
@click.pass_context
def validate(ctx):
    root_dir = ctx.obj["ROOT_DIR"]
    EnvValidator(root_dir).prepare_env()


if __name__ == "__main__":
    cli(obj={})
