import json

from pykube.objects import NamespacedAPIObject

from .scalable import Scalable, DOWNSCALER_SAVED_ANNOTATION


class StackSet(NamespacedAPIObject, Scalable):
    """
    Use latest workloads API version (apps/v1), pykube is stuck with old version
    """

    version = "zalando.org/v1"
    endpoint = "stacksets"
    kind = "StackSet"

    def set_replicas(self, count):
        self.obj['spec']['stackTemplate']['spec']['replicas'] = count

    def get_replicas(self):
        return int(self.obj['spec']['stackTemplate']['spec']['replicas'])

    def save_state(self):
        self.annotations[DOWNSCALER_SAVED_ANNOTATION] = json.dumps(
            self.obj['spec']['stackTemplate']['spec']['horizontalPodAutoscaler'])
        self.obj['spec']['stackTemplate']['spec']['horizontalPodAutoscaler'] = None
