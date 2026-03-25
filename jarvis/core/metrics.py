"""
Suivi des performances et métriques du système
"""
import time
import functools
import logging
from typing import Callable, Dict, List
from collections import defaultdict
from statistics import mean, stdev


logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Collecte et analyse les métriques de performance"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
    
    def timer(self, metric_name: str):
        """Décorateur pour mesurer le temps d'exécution"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.time() - start_time
                    self.metrics[metric_name].append(elapsed)
                    logger.info(
                        f"⏱️ {func.__name__} took {elapsed:.3f}s"
                    )
            return wrapper
        return decorator
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Obtenir les statistiques pour une métrique"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
        
        times = self.metrics[metric_name]
        stats = {
            "count": len(times),
            "min": min(times),
            "max": max(times),
            "avg": mean(times),
        }
        
        if len(times) > 1:
            stats["stddev"] = stdev(times)
        
        return stats
    
    def print_all_stats(self):
        """Afficher toutes les statistiques"""
        print("\n" + "="*60)
        print("📊 MÉTRIQUES DE PERFORMANCE")
        print("="*60)
        
        for metric_name in sorted(self.metrics.keys()):
            stats = self.get_stats(metric_name)
            if stats:
                print(f"\n{metric_name}:")
                print(f"  • Count: {stats['count']}")
                print(f"  • Min: {stats['min']:.3f}s")
                print(f"  • Max: {stats['max']:.3f}s")
                print(f"  • Avg: {stats['avg']:.3f}s")
                if "stddev" in stats:
                    print(f"  • StdDev: {stats['stddev']:.3f}s")
        
        print("\n" + "="*60 + "\n")


# Instance globale
metrics = PerformanceMetrics()
