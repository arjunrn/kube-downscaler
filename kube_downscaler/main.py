#!/usr/bin/env python3

import time

import logging

from kube_downscaler import cmd, shutdown
from kube_downscaler.scaler import scale

logger = logging.getLogger('downscaler')


def main():
    parser = cmd.get_parser()
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.DEBUG if args.debug else logging.INFO)

    handler = shutdown.GracefulShutdown()

    logger.info('Downscaler started with config: %s', args)

    if args.dry_run:
        logger.info('**DRY-RUN**: no downscaling will be performed!')

    while True:
        try:
            scale(args.namespace, args.default_uptime, args.default_downtime,
                  kinds=frozenset(args.kind),
                  exclude_namespaces=frozenset(args.exclude_namespaces.split(',')),
                  exclude_deployments=frozenset(args.exclude_deployments.split(',')),
                  exclude_statefulsets=frozenset(args.exclude_statefulsets.split(',')),
                  dry_run=args.dry_run, grace_period=args.grace_period)
        except Exception:
            logger.exception('Failed to autoscale')
        if args.once or handler.shutdown_now:
            return
        with handler.safe_exit():
            time.sleep(args.interval)
