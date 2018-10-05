from pykube.mixins import ReplicatedMixin, ScalableMixin
from pykube.objects import NamespacedAPIObject


class Deployment(NamespacedAPIObject, ReplicatedMixin, ScalableMixin):
    """
    Use latest workloads API version (apps/v1), pykube is stuck with old version
    """

    version = "apps/v1"
    endpoint = "deployments"
    kind = "Deployment"


class Statefulset(NamespacedAPIObject, ReplicatedMixin, ScalableMixin):
    """
    Use latest workloads API version (apps/v1), pykube is stuck with old version
    """

    version = "apps/v1"
    endpoint = "statefulsets"
    kind = "StatefulSet"


class StackSet(NamespacedAPIObject, ReplicatedMixin, ScalableMixin):
    """
    Use latest workloads API version (apps/v1), pykube is stuck with old version
    """

    version = "zalando.org/v1"
    endpoint = "stacksets"
    kind = "StackSet"
