import requests
from typing import Dict, Optional

BASE_URL = "https://api005.dnshe.com/index.php?m=domain_hub"

class DnsheClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = {
            "X-API-Key": api_key,
            "X-API-Secret": api_secret,
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, action: str, params: Optional[Dict] = None) -> Dict:
        query = {"endpoint": endpoint, "action": action}
        if params:
            query.update(params)
        r = requests.get(BASE_URL, headers=self.headers, params=query, timeout=15)
        return r.json()

    def _post(self, endpoint: str, action: str, data: Optional[Dict] = None, extra_params: Optional[Dict] = None) -> Dict:
        params = {"endpoint": endpoint, "action": action}
        if extra_params:
            params.update(extra_params)
        r = requests.post(BASE_URL, headers=self.headers, params=params, json=data, timeout=15)
        # 兼容空响应/非JSON响应
        try:
            return r.json()
        except:
            return {"success": True, "message": "操作成功", "raw_status": r.status_code, "raw_text": r.text[:200]}

    # ========== 子域名管理 ==========
    def list_subdomains(self) -> Dict:
        return self._get("subdomains", "list", {"per_page": 500})

    def get_available_root_domains(self) -> Dict:
        """从已有域名提取根域名"""
        return self.list_subdomains()

    def register_subdomain(self, subdomain: str, rootdomain: str) -> Dict:
        """注册子域名（官方action是register，不是create）"""
        return self._post("subdomains", "register", {
            "subdomain": subdomain,
            "rootdomain": rootdomain
        })

    def renew_subdomain(self, subdomain_id: int) -> Dict:
        return self._post("subdomains", "renew", {
            "subdomain_id": subdomain_id
        })

    def delete_subdomain(self, subdomain_id: int) -> Dict:
        # 参数同时放在URL query和body里，兼容这个接口的特殊要求
        params = {"subdomain_id": subdomain_id}
        return self._post("subdomains", "delete", {"subdomain_id": subdomain_id}, extra_params=params)

    # ========== DNS记录管理 ==========
    def list_dns_records(self, subdomain_id: int) -> Dict:
        return self._get("dns_records", "list", {"subdomain_id": subdomain_id})

    def create_dns_record(self, subdomain_id: int, rtype: str, name: str, content: str, ttl: int = 600) -> Dict:
        """创建DNS记录，主机字段是name，不是host"""
        return self._post("dns_records", "create", {
            "subdomain_id": subdomain_id,
            "type": rtype,
            "name": name,
            "content": content,
            "ttl": ttl
        })

    def update_dns_record(self, record_id: int, rtype: str, name: str, content: str, ttl: int = 600) -> Dict:
        return self._post("dns_records", "update", {
            "id": record_id,
            "type": rtype,
            "name": name,
            "content": content,
            "ttl": ttl
        })

    def delete_dns_record(self, record_id: int) -> Dict:
        return self._post("dns_records", "delete", {
            "id": record_id
        })

    # ========== 配额查询 ==========
    def get_quota(self) -> Dict:
        return self._get("quota", "info")
