"""Helper class to extract data from input json send to /api/v1/user-repo/scan endpoint."""


class DataExtractor:
    """Exracts direct and transitive deps from a given json."""

    @classmethod
    def get_details_from_results(cls, details_):
        """Get information from details_."""
        set_direct = set()
        set_transitive = set()
        for detail_ in details_:
            ecosystem_ = detail_.get("ecosystem", None)
            resolved_ = detail_.get("_resolved", None)
            cls.get_res_data(ecosystem_, resolved_, set_transitive, set_direct)

        return set_direct, set_transitive

    @classmethod
    def get_res_data(cls, ecosystem_, resolved_, set_transitive, set_direct):
        """Get information from resolved."""
        for res_ in resolved_:
            dir_package = res_.get("package", None)
            dir_version = res_.get("version", None)
            set_direct.add(ecosystem_ + ":" + dir_package + ":" + dir_version)
            transdeps = res_.get("deps", None)
            if transdeps is not None:
                cls.get_trans_data(ecosystem_, transdeps, set_transitive)

    def get_trans_data(ecosystem_, transdeps, set_transitive):
        """Get information from each dependency dictionary."""
        if transdeps is None:
            raise Exception("transitive dependencies not present")
        for dep_ in transdeps:
            trans_package = dep_.get("package", None)
            trans_version = dep_.get("version", None)
            set_transitive.add(ecosystem_ + ":" + trans_package + ":" + trans_version)
