import datetime
import logging
import pykube
from typing import FrozenSet

from kube_downscaler import helper
from kube_downscaler.resources import Deployment, Statefulset, StackSet

logger = logging.getLogger(__name__)
ORIGINAL_REPLICAS_ANNOTATION = 'downscaler/original-replicas'


def within_grace_period(deploy, grace_period: int):
    creation_time = datetime.datetime.strptime(deploy.metadata['creationTimestamp'], '%Y-%m-%dT%H:%M:%SZ')
    now = datetime.datetime.utcnow()
    delta = now - creation_time
    return delta.total_seconds() <= grace_period


def pods_force_uptime(api, namespace: str):
    """Returns True if there are any running pods which require the deployments to be scaled back up"""
    for pod in pykube.Pod.objects(api).filter(namespace=(namespace or pykube.all)):
        if pod.obj.get('status', {}).get('phase') in ('Succeeded', 'Failed'):
            continue
        if pod.annotations.get('downscaler/force-uptime') == 'true':
            logger.info('Forced uptime because of %s/%s', pod.namespace, pod.name)
            return True
    return False


def autoscale_resource(resource: pykube.objects.NamespacedAPIObject,
                       default_uptime: str, default_downtime: str, forced_uptime: bool, dry_run: bool,
                       now: datetime.datetime, grace_period: int):
    try:
        # any value different from "false" will ignore the resource (to be on the safe side)
        exclude = resource.annotations.get('downscaler/exclude', 'false') != 'false'
        if exclude:
            logger.debug('%s %s/%s was excluded', resource.kind, resource.namespace, resource.name)
        else:
            replicas = resource.obj['spec']['replicas']

            if forced_uptime:
                uptime = "forced"
                downtime = "ignored"
                is_uptime = True
            else:
                uptime = resource.annotations.get('downscaler/uptime', default_uptime)
                downtime = resource.annotations.get('downscaler/downtime', default_downtime)
                is_uptime = helper.matches_time_spec(now, uptime) and not helper.matches_time_spec(now, downtime)

            original_replicas = resource.annotations.get(ORIGINAL_REPLICAS_ANNOTATION)
            logger.debug('%s %s/%s has %s replicas (original: %s, uptime: %s)',
                         resource.kind, resource.namespace, resource.name, replicas, original_replicas, uptime)
            update_needed = False
            if is_uptime and replicas == 0 and original_replicas and int(original_replicas) > 0:
                logger.info('Scaling up %s %s/%s from %s to %s replicas (uptime: %s, downtime: %s)',
                            resource.kind, resource.namespace, resource.name, replicas, original_replicas,
                            uptime, downtime)
                resource.obj['spec']['replicas'] = int(original_replicas)
                resource.annotations[ORIGINAL_REPLICAS_ANNOTATION] = None
                update_needed = True
            elif not is_uptime and replicas > 0:
                if within_grace_period(resource, grace_period):
                    logger.info('%s %s/%s within grace period (%ds), not scaling down (yet)',
                                resource.kind, resource.namespace, resource.name, grace_period)
                else:
                    target_replicas = 0
                    logger.info('Scaling down %s %s/%s from %s to %s replicas (uptime: %s, downtime: %s)',
                                resource.kind, resource.namespace, resource.name, replicas, target_replicas,
                                uptime, downtime)
                    resource.annotations[ORIGINAL_REPLICAS_ANNOTATION] = str(replicas)
                    resource.obj['spec']['replicas'] = target_replicas
                    update_needed = True
            if update_needed:
                if dry_run:
                    logger.info('**DRY-RUN**: would update %s %s/%s', resource.kind, resource.namespace, resource.name)
                else:
                    resource.update()
    except Exception:
        logger.exception('Failed to process %s %s/%s', resource.kind, resource.namespace, resource.name)


def autoscale_resources(api, kind, namespace: str,
                        exclude_namespaces: FrozenSet[str], exclude_names: FrozenSet[str],
                        default_uptime: str, default_downtime: str, forced_uptime: bool, dry_run: bool,
                        now: datetime.datetime, grace_period: int):
    for resource in kind.objects(api, namespace=(namespace or pykube.all)):
        if resource.namespace in exclude_namespaces or resource.name in exclude_names:
            continue
        autoscale_resource(resource, default_uptime, default_downtime, forced_uptime, dry_run, now, grace_period)


def scale(namespace: str, default_uptime: str, default_downtime: str, kinds: FrozenSet[str],
          exclude_namespaces: FrozenSet[str],
          exclude_deployments: FrozenSet[str],
          exclude_statefulsets: FrozenSet[str],
          dry_run: bool, grace_period: int):
    api = helper.get_kube_api()

    now = datetime.datetime.utcnow()
    forced_uptime = pods_force_uptime(api, namespace)

    if 'deployment' in kinds:
        autoscale_resources(api, Deployment, namespace, exclude_namespaces, exclude_deployments,
                            default_uptime, default_downtime, forced_uptime, dry_run, now, grace_period)
    if 'statefulset' in kinds:
        autoscale_resources(api, Statefulset, namespace, exclude_namespaces, exclude_statefulsets,
                            default_uptime, default_downtime, forced_uptime, dry_run, now, grace_period)
    if 'stackset' in kinds:
        autoscale_resources(api, StackSet, namespace, exclude_namespaces, exclude_statefulsets,
                            default_uptime, default_downtime, forced_uptime, dry_run, now, grace_period)
