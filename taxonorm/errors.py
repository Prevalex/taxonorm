"""
This taxonorm package module is designed to define custom exception.

    How to use:
    ----------

def load_file(path: str):
    return parse_file(path)

def parse_file(path: str):
    raise ParsingError(
        "Cannot parse taxonomy file",
        context={"path": path})

try:
    load_file("categories.csv")
except TaxonormError as e:
    print(str(e))
    print(e.to_dict())


    How to log:
    ----------

try:
    result = parse_taxonomy(path)
except TaxonormError as e:
    logger.exception(
        "Taxonorm operation failed",
        extra={
            "error_code": e.code,
            "context": e.context,
        },
    )
"""
import sys
from typing import Any



class TaxonormError(Exception):
    code = "taxonorm_error"

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        capture_location: bool = True,
    ):
        super().__init__(message)

        self.message = message
        self.context = context or {}

        # Tuple:
        #   location[0] - caller above the error site
        #   location[1] - function where the exception was created
        self.location: tuple[str | None, str | None] | None = None

        if capture_location:
            self._capture_location()

    def _capture_location(self) -> None:
        try:
            # 0 = _capture_location
            # 1 = __init__
            # 2 = exception creation site: raise ParsingError(...)
            # 3 = caller above it
            error_frame = sys._getframe(2)
            caller_frame = error_frame.f_back

            error_location = self._format_frame_location(error_frame)
            caller_location = (
                self._format_frame_location(caller_frame)
                if caller_frame is not None
                else None
            )

            self.location = (caller_location, error_location)

        except ValueError:
            self.location = None

    @staticmethod
    def _format_frame_location(frame) -> str:
        module = frame.f_globals.get("__name__")
        function = frame.f_code.co_name
        return f"{module}.{function}"

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }

        if self.location:
            data["location"] = self.location

        if self.context:
            data["context"] = self.context

        return data

class TxParsingError(TaxonormError):
    code = "parsing_error"

class TxValidationError(TaxonormError):
    code = "validation_error"

class TxInputValidationError(TxValidationError):
    """External taxonomy data failed user-facing validation."""

    code = "input_validation_error"

    def __init__(self, report: Any):
        self.report = report
        super().__init__(
            report.format_text(),
            context={"validation": report.to_dict()},
        )

class TxConversionError(TaxonormError):
    code = "conversion_error"

class TxHandlingError(TaxonormError):
    code = "handling_error"

class TxExportError(TaxonormError):
    code = "export_error"

class TxImportError(TaxonormError):
    code = "import_error"

class TxInternalError(TaxonormError):
    code = "internal_error"

class TxNotImplementedError(TaxonormError):
    code = "not_implemented_error"


    
