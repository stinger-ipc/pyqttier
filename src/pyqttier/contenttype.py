import re
from typing import Dict, Union


class ContentType(str):
    """
    A string subclass representing an HTTP Content-Type.
    Main value: 'type/subtype'
    Attributes: parameters (e.g., charset, boundary)
    """

    parameters: Dict[str, str]

    def __new__(cls, content_type_header: Union[str, "ContentType"]):
        if isinstance(content_type_header, ContentType):
            obj = super().__new__(cls, str(content_type_header))
            obj.parameters = dict(content_type_header.parameters)
            for key, val in obj.parameters.items():
                if key.isidentifier():
                    setattr(obj, key, val)
            return obj

        if not content_type_header or not content_type_header.strip():
            raise ValueError("Content-Type header cannot be empty.")

        # 1. Separate main media type from parameter block
        parts = content_type_header.split(";", 1)
        full_type = parts[0].strip().lower()

        if "/" not in full_type:
            raise ValueError(f"Invalid Content-Type format: '{parts[0]}'")

        # 2. Instantiate the str primitive with 'type/subtype'
        obj = super().__new__(cls, full_type)

        # 3. Parse parameters
        params = {}
        if len(parts) > 1:
            param_pattern = re.compile(
                r';\s*([^\s=;]+)=(?:"((?:[^\\"]|\\.)*)"|([^\s;]+))'
            )
            param_string = ";" + parts[1]

            for match in param_pattern.finditer(param_string):
                key = match.group(1).lower()
                quoted_val = match.group(2)
                unquoted_val = match.group(3)

                # Unescape quoted strings if present
                if quoted_val is not None:
                    value = re.sub(r"\\(.)", r"\1", quoted_val)
                else:
                    value = unquoted_val

                params[key] = value

        # 4. Attach parameter dict and set each parameter as an attribute
        obj.parameters = params
        for key, val in params.items():
            # Use valid Python identifiers or fallback access via obj.parameters
            if key.isidentifier():
                setattr(obj, key, val)

        return obj

    def to_header(self) -> str:
        """
        Reconstruct the full Content-Type header string, including parameters.
        """
        header = str(self)
        for key, value in self.parameters.items():
            if re.search(r'[\s";=]', value):
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                header += f'; {key}="{escaped}"'
            else:
                header += f"; {key}={value}"
        return header
