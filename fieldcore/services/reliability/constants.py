class PendingAction:
    NONE = "NONE"
    SEND_ACTIVE = "SEND_ACTIVE"
    SEND_INACTIVE = "SEND_INACTIVE"


class OutboxStatus:
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class StateCategory:
    ALARM = "ALARM"
    DEVICE = "DEVICE"
    CONNECTION = "CONNECTION"
