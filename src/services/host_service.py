import asyncio
from typing import Optional
from src.management.logger import configure_logger

logger = configure_logger("HostService", "cyan")


class HostService:
    @staticmethod
    async def run_command(cmd: str, timeout: int = 2000, check: bool = True) -> tuple[str, str]:
        logger.debug(f"Executing host command: {cmd}")

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout / 1000
            )
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Command timed out after {timeout}ms: {cmd}")

        stdout_decoded = stdout.decode().strip()
        stderr_decoded = stderr.decode().strip()

        if check and process.returncode != 0:
            logger.error(
                f"Host command failed with code {process.returncode}: {stderr_decoded}"
            )
            raise RuntimeError(
                f"Command failed: {stderr_decoded or 'Unknown error'}"
            )

        return stdout_decoded, stderr_decoded

    @staticmethod
    async def list_running_containers() -> set[str]:
        try:
            stdout, _ = await HostService.run_command(
                "docker ps --format '{{.Names}}'",
                timeout=1500,
                check=False
            )

            containers = set(
                line.strip()
                for line in stdout.split("\n")
                if line.strip()
            )

            logger.debug(f"Found {len(containers)} running containers")
            return containers

        except Exception as e:
            logger.warning(f"Failed to list Docker containers: {e}")
            return set()

    @staticmethod
    async def is_container_running(container_name: str) -> bool:
        if not container_name:
            return False

        containers = await HostService.list_running_containers()
        return container_name in containers

    @staticmethod
    async def get_container_port(container_name: str, protocol: str = "udp") -> Optional[int]:
        try:
            cmd = f"docker port {container_name} | grep '{protocol}' | head -1 | cut -d ':' -f 2"
            stdout, _ = await HostService.run_command(cmd, timeout=1500, check=False)

            if stdout:
                return int(stdout)

            return None

        except Exception as e:
            logger.warning(f"Failed to get port for container {container_name}: {e}")
            return None

    @staticmethod
    async def read_file(path: str) -> str:
        stdout, _ = await HostService.run_command(f"cat {path}")
        return stdout

    @staticmethod
    async def get_system_info() -> dict:
        import os

        try:
            cpu_count = os.cpu_count() or 1

            loadavg = os.getloadavg()

            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu": {
                    "cores": cpu_count,
                },
                "loadavg": list(loadavg),
                "memory": {
                    "total_bytes": mem.total,
                    "free_bytes": mem.available,
                    "used_bytes": mem.used,
                },
                "disk": {
                    "total_bytes": disk.total,
                    "used_bytes": disk.used,
                    "available_bytes": disk.free,
                    "used_percent": disk.percent,
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}
