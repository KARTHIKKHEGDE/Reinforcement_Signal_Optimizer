"""
RL Agent Evaluation System
==========================
Comprehensive evaluation of trained PPO agent on real-world traffic data.

Evaluation Strategy:
1. Load trained RL policy
2. Test on all 24 hours of Silk Board data
3. Run multiple episodes per hour (statistical robustness)
4. Calculate comprehensive metrics
5. Save detailed results for comparison

Output:
- results/rl_evaluation.csv (detailed metrics)
- results/rl_episodes/ (episode-by-episode data)
- results/rl_summary.txt (aggregated statistics)

Usage:
    python evaluate.py --model models/best_model.zip
    python evaluate.py --model models/best_model.zip --episodes 5
"""

import os
import sys
import numpy as np
import pandas as pd
import argparse
from typing import Dict, List, Tuple
from datetime import datetime
import json

# Gymnasium and RL
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Our modules
# Our modules
from environment.traffic_env import TrafficEnv
from utils.arrival_rate_converter import get_hourly_rates


# ============================================
# GYMNASIUM WRAPPER (Evaluation Version)
# ============================================

class EvalTrafficEnv(gym.Env):
    """
    Evaluation-only wrapper (no training features).
    Simpler and faster than training wrapper.
    """
    
    metadata = {"render_modes": ["human"]}
    
    def __init__(self, max_steps: int = 3600):
        super().__init__()
        
        self.env = TrafficEnv(
            max_steps=max_steps,
            saturation_flow_rate=0.53,
            lanes_per_direction=2,
            track_waiting_time=True,
        )
        
        self.observation_space = spaces.Box(
            low=0.0,
            high=5.0,
            shape=(self.env.state_dim,),
            dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(self.env.n_actions)
    
    def reset(self, seed=None, arrival_rates=None):
        super().reset(seed=seed)
        obs = self.env.reset(arrival_rates=arrival_rates)
        info = {"arrival_rates": self.env.arrival_rates}
        return obs.astype(np.float32), info
    
    def step(self, action):
        obs, reward, done, info = self.env.step(action)
        truncated = False
        return obs.astype(np.float32), reward, done, truncated, info
    
    def get_metrics(self):
        return self.env.get_metrics()
    
    def render(self):
        pass
    
    def close(self):
        pass


# ============================================
# EVALUATION ENGINE
# ============================================

class RLEvaluator:
    """
    Evaluates trained RL agent on real traffic scenarios.
    
    Metrics tracked:
    - Average queue length
    - Total waiting time
    - Throughput (vehicles served)
    - Average vehicle delay
    - Queue imbalance (fairness)
    - Episode reward
    """
    
    def __init__(self, model_path: str, verbose: bool = True):
        """
        Initialize evaluator.
        
        Args:
            model_path: Path to trained PPO model (.zip)
            verbose: Print progress
        """
        self.verbose = verbose
        
        # Load trained model
        if self.verbose:
            print(f"📦 Loading model: {model_path}")
        
        try:
            self.model = PPO.load(model_path)
            if self.verbose:
                print(f"   ✓ Model loaded successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
        
        # Create evaluation environment
        self.env = EvalTrafficEnv(max_steps=3600)
        
        if self.verbose:
            print(f"   ✓ Evaluation environment ready")
    
    def evaluate_single_episode(
        self,
        arrival_rates: Dict[str, float],
        deterministic: bool = True,
        seed: int = None
    ) -> Dict:
        """
        Run one episode with given arrival rates.
        
        Args:
            arrival_rates: {'north': λ, 'south': λ, 'east': λ, 'west': λ}
            deterministic: Use deterministic policy (no exploration)
            seed: Random seed for reproducibility
        
        Returns:
            Dictionary with episode metrics
        """
        obs, info = self.env.reset(seed=seed, arrival_rates=arrival_rates)
        
        done = False
        truncated = False
        episode_reward = 0.0
        step_count = 0
        
        # Track step-by-step data
        queue_history = []
        action_history = []
        phase_history = []
        
        while not (done or truncated):
            # Get action from trained policy
            action, _ = self.model.predict(obs, deterministic=deterministic)
            
            # Execute action
            obs, reward, done, truncated, info = self.env.step(action)
            
            # Track metrics
            episode_reward += reward
            step_count += 1
            queue_history.append(info['total_queue'])
            action_history.append(int(action))
            phase_history.append(int(info['phase']))
        
        # Get final metrics from environment
        metrics = self.env.get_metrics()
        
        # Add episode-specific data
        metrics.update({
            'episode_reward': episode_reward,
            'episode_steps': step_count,
            'arrival_rates': arrival_rates.copy(),
            'queue_history': queue_history,
            'action_history': action_history,
            'phase_history': phase_history,
            'avg_queue_per_step': np.mean(queue_history),
            'max_queue_reached': np.max(queue_history),
            'queue_std': np.std(queue_history),
        })
        
        return metrics
    
    def evaluate_hour(
        self,
        hour: int,
        arrival_rates_csv: str,
        n_episodes: int = 5,
        deterministic: bool = True
    ) -> Dict:
        """
        Evaluate on a specific hour with multiple episodes.
        
        Args:
            hour: Hour of day (0-23)
            arrival_rates_csv: Path to arrival rates CSV
            n_episodes: Number of episodes to average over
            deterministic: Use deterministic policy
        
        Returns:
            Aggregated metrics across episodes
        """
        if self.verbose:
            print(f"\n⏰ Evaluating Hour {hour:02d}:00")
        
        # Get arrival rates for this hour
        try:
            rates = get_hourly_rates(arrival_rates_csv, hour)
            if self.verbose:
                print(f"   Arrival rates: N={rates['north']:.2f}, S={rates['south']:.2f}, "
                      f"E={rates['east']:.2f}, W={rates['west']:.2f} veh/sec")
        except Exception as e:
            raise RuntimeError(f"Failed to load rates for hour {hour}: {e}")
        
        # Run multiple episodes
        episode_results = []
        for ep in range(n_episodes):
            if self.verbose:
                print(f"   Episode {ep+1}/{n_episodes}...", end=' ')
            
            result = self.evaluate_single_episode(
                arrival_rates=rates,
                deterministic=deterministic,
                seed=hour * 100 + ep  # Reproducible seeds
            )
            episode_results.append(result)
            
            if self.verbose:
                print(f"Avg Queue: {result['avg_queue_length']:.2f}, "
                      f"Delay: {result['avg_vehicle_delay']:.2f}s, "
                      f"Reward: {result['episode_reward']:.2f}")
        
        # Aggregate metrics
        aggregated = self._aggregate_episodes(episode_results)
        aggregated['hour'] = hour
        aggregated['n_episodes'] = n_episodes
        
        return aggregated
    
    def evaluate_full_day(
        self,
        arrival_rates_csv: str,
        n_episodes_per_hour: int = 5,
        output_dir: str = "results"
    ) -> pd.DataFrame:
        """
        Evaluate on all 24 hours of the day.
        
        Args:
            arrival_rates_csv: Path to CSV with hourly arrival rates
            n_episodes_per_hour: Episodes per hour for statistical robustness
            output_dir: Directory to save results
        
        Returns:
            DataFrame with hourly results
        """
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/rl_episodes", exist_ok=True)
        
        print("=" * 80)
        print("🚦 FULL DAY EVALUATION - RL AGENT")
        print("=" * 80)
        print(f"Model: {self.model}")
        print(f"Episodes per hour: {n_episodes_per_hour}")
        print(f"Total episodes: {24 * n_episodes_per_hour}")
        print("=" * 80)
        
        all_results = []
        
        for hour in range(24):
            result = self.evaluate_hour(
                hour=hour,
                arrival_rates_csv=arrival_rates_csv,
                n_episodes=n_episodes_per_hour,
                deterministic=True
            )
            all_results.append(result)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        
        # Save detailed results
        output_file = f"{output_dir}/rl_evaluation.csv"
        df.to_csv(output_file, index=False)
        
        if self.verbose:
            print(f"\n💾 Results saved: {output_file}")
        
        # Generate summary
        self._generate_summary(df, output_dir)
        
        return df
    
    def _aggregate_episodes(self, episode_results: List[Dict]) -> Dict:
        """Aggregate metrics across multiple episodes."""
        aggregated = {}
        
        # Numeric metrics to average
        numeric_keys = [
            'avg_queue_length', 'total_throughput', 'throughput_per_step',
            'total_delay_seconds', 'avg_vehicle_delay', 'queue_imbalance',
            'max_queue_reached', 'episode_reward', 'avg_queue_per_step',
            'queue_std'
        ]
        
        for key in numeric_keys:
            values = [r[key] for r in episode_results if key in r]
            if len(values) > 0:
                aggregated[f"{key}_mean"] = np.mean(values)
                aggregated[f"{key}_std"] = np.std(values)
                aggregated[f"{key}_min"] = np.min(values)
                aggregated[f"{key}_max"] = np.max(values)
        
        # Keep arrival rates from first episode
        aggregated['arrival_rates'] = episode_results[0]['arrival_rates']
        
        return aggregated
    
    def _generate_summary(self, df: pd.DataFrame, output_dir: str):
        """Generate human-readable summary report."""
        summary_file = f"{output_dir}/rl_summary.txt"
        
        with open(summary_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("RL AGENT EVALUATION SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Hours Evaluated: 24\n")
            f.write(f"Episodes per Hour: {df['n_episodes'].iloc[0]}\n\n")
            
            f.write("OVERALL PERFORMANCE:\n")
            f.write("-" * 80 + "\n")
            f.write(f"  Average Queue Length:  {df['avg_queue_length_mean'].mean():.2f} ± {df['avg_queue_length_std'].mean():.2f} vehicles\n")
            f.write(f"  Average Vehicle Delay: {df['avg_vehicle_delay_mean'].mean():.2f} ± {df['avg_vehicle_delay_std'].mean():.2f} seconds\n")
            f.write(f"  Total Throughput:      {df['total_throughput_mean'].mean():.0f} ± {df['total_throughput_std'].mean():.0f} vehicles/hour\n")
            f.write(f"  Queue Imbalance:       {df['queue_imbalance_mean'].mean():.2f} ± {df['queue_imbalance_std'].mean():.2f}\n")
            f.write(f"  Average Reward:        {df['episode_reward_mean'].mean():.3f} ± {df['episode_reward_std'].mean():.3f}\n\n")
            
            f.write("PEAK HOUR PERFORMANCE:\n")
            f.write("-" * 80 + "\n")
            # Morning peak (8 AM)
            morning = df[df['hour'] == 8].iloc[0]
            f.write(f"  Morning Peak (08:00):\n")
            f.write(f"    Avg Queue: {morning['avg_queue_length_mean']:.2f} vehicles\n")
            f.write(f"    Avg Delay: {morning['avg_vehicle_delay_mean']:.2f} seconds\n\n")
            
            # Evening peak (18:00)
            evening = df[df['hour'] == 18].iloc[0]
            f.write(f"  Evening Peak (18:00):\n")
            f.write(f"    Avg Queue: {evening['avg_queue_length_mean']:.2f} vehicles\n")
            f.write(f"    Avg Delay: {evening['avg_vehicle_delay_mean']:.2f} seconds\n\n")
            
            f.write("BEST PERFORMANCE HOUR:\n")
            f.write("-" * 80 + "\n")
            best_hour = df.loc[df['avg_queue_length_mean'].idxmin()]
            f.write(f"  Hour: {int(best_hour['hour']):02d}:00\n")
            f.write(f"  Avg Queue: {best_hour['avg_queue_length_mean']:.2f} vehicles\n")
            f.write(f"  Avg Delay: {best_hour['avg_vehicle_delay_mean']:.2f} seconds\n\n")
            
            f.write("WORST PERFORMANCE HOUR:\n")
            f.write("-" * 80 + "\n")
            worst_hour = df.loc[df['avg_queue_length_mean'].idxmax()]
            f.write(f"  Hour: {int(worst_hour['hour']):02d}:00\n")
            f.write(f"  Avg Queue: {worst_hour['avg_queue_length_mean']:.2f} vehicles\n")
            f.write(f"  Avg Delay: {worst_hour['avg_vehicle_delay_mean']:.2f} seconds\n\n")
            
            f.write("=" * 80 + "\n")
        
        if self.verbose:
            print(f"📄 Summary saved: {summary_file}")
    
    def close(self):
        """Clean up resources."""
        self.env.close()


# ============================================
# COMMAND-LINE INTERFACE
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate trained RL agent on Silk Board traffic data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to trained model (.zip file)"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="silk_board_arrival_rates.csv",
        help="Path to arrival rates CSV"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=5,
        help="Number of episodes per hour"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=None,
        help="Evaluate single hour only (0-23)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.model):
        print(f"❌ Error: Model file not found: {args.model}")
        sys.exit(1)
    
    if not os.path.exists(args.data):
        print(f"❌ Error: Data file not found: {args.data}")
        sys.exit(1)
    
    # Create evaluator
    evaluator = RLEvaluator(
        model_path=args.model,
        verbose=not args.quiet
    )
    
    try:
        if args.hour is not None:
            # Single hour evaluation
            result = evaluator.evaluate_hour(
                hour=args.hour,
                arrival_rates_csv=args.data,
                n_episodes=args.episodes
            )
            print(f"\n📊 Results for Hour {args.hour:02d}:00:")
            print(f"   Avg Queue: {result['avg_queue_length_mean']:.2f} ± {result['avg_queue_length_std']:.2f}")
            print(f"   Avg Delay: {result['avg_vehicle_delay_mean']:.2f} ± {result['avg_vehicle_delay_std']:.2f}s")
            print(f"   Throughput: {result['total_throughput_mean']:.0f} ± {result['total_throughput_std']:.0f} veh")
        else:
            # Full day evaluation
            results_df = evaluator.evaluate_full_day(
                arrival_rates_csv=args.data,
                n_episodes_per_hour=args.episodes,
                output_dir=args.output
            )
            
            print("\n" + "=" * 80)
            print("✅ EVALUATION COMPLETE!")
            print("=" * 80)
            print(f"\nResults saved to: {args.output}/")
            print(f"  - rl_evaluation.csv  (detailed metrics)")
            print(f"  - rl_summary.txt     (summary report)")
            print(f"\nNext: Run baseline.py to compare with fixed-time control")
    
    finally:
        evaluator.close()


if __name__ == "__main__":
    main()