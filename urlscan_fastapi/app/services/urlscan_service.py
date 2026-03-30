def get_report(self, uuid: str):
    success, result = self.client.get_report(uuid)

    if not success:
        return {"success": False, "error": result}

    return {
        "success": True,
        "url": result.get("task", {}).get("url"),
        "ip": result.get("page", {}).get("ip"),
        "country": result.get("page", {}).get("country"),
        "full_response": result
    }


def lookup_domain(self, domain: str):
    success, result = self.client.lookup_domain(domain)

    if not success:
        return {"success": False, "error": result}

    return {
        "success": True,
        "results": result.get("results", [])
    }