from dataclasses import dataclass, field


@dataclass
class ResultBundle:
    success: bool
    message: str
    validation_errors: list
    log_lines: list = field(default_factory=list)
    output_paths: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    ahp_result: dict = field(default_factory=dict)
