"""
Fixed-Time Baseline Controller Evaluation
=========================================
Evaluates traditional fixed-time signal control for comparison with RL.

Baseline Strategy:
- Webster's optimal cycle time formula
- Pre-calculated green splits based on typical traffic patterns
- No adaptation (same timing all day)

This represents current real-world practice at many intersections.

Usage:
    python baseline.py
    python baseline.py --episodes 5 --output results
"""

import os
import sys
import numpy as np
import pandas as pd
import argparse
from typing import Dict, List
from datetime import datetime

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Our modules
# Our modules
from environment.traffic_env import TrafficEnv
from utils.arrival_rate_converter import get_hourly_rates


# ============================================
# FIXED-TIME SIGNAL CONTROLLER
# ============================================

class FixedTimeController:
    """
    Traditional fixed-time signal controller.
    
    Design based on Webster's formula:
    - Optimal cycle time: C = (1.5L + 5) / (1 - Y)
    - Where L = lost time, Y = critical flow ratio
    
    For Silk Board (typical urban intersection):
    - Cycle time: 120 seconds
    - Green splits: NS-Through(30s), NS-Left(10s), EW-Through(30s), EW-Left(10s)
    - Yellow: 3s per phase
    - All-red: 2s per phase
    
    This is representative of current practice in many Indian cities.
    """
    
    def __init__(
        self,
        cycle_time: int = 120,
        green_splits: List[int] = None,
        yellow_time: int = 3,
        all_red_time: int = 2
    ):
        """
        Initialize fixed-time controller.
        
        Args:
            cycle_time: Total cycle length in seconds
            green_splits: Green time for each phase [NS_G, NS_L, EW_G, EW_L]
            yellow_time: Yellow clearance interval
            all_red_time: All-red clearance interval
        """
        self.cycle_time = cycle_time
        self.green_splits = green_splits or [30, 10, 30, 10]
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time
        
        # Validate cycle time
        total_effective = sum(self.green_splits) + 4 * (yellow_time + all_red_time)
        if total_effective > cycle_time:
            raise ValueError(f"Green splits + clearances ({total_effective}s) exceed cycle time ({cycle_time}s)")
        
        # State tracking
        self.current_phase = 0
        self.phase_timer = self.green_splits[0]
        self.in_yellow = False
        self.in_all_red = False
        self.yellow_timer = 0
        self.all_red_timer = 0
        self.step_count = 0
    
    def get_action(self, obs: np.ndarray = None) -> int:
        """
        Get next action (ignores observation - fixed-time).
        
        Args:
            obs: State observation (ignored for fixed-time)
        
        Returns:
            Action: 0=extend, 1-4=switch to phase
        """
        self.step_count += 1
        
        # Handle yellow phase
        if self.in_yellow:
            self.yellow_timer -= 1
            if self.yellow_timer <= 0:
                self.in_yellow = False
                self.in_all_red = True
                self.all_red_timer = self.all_red_time
            return 0  # Extend (no action during yellow)
        
        # Handle all-red phase
        if self.in_all_red:
            self.all_red_timer -= 1
            if self.all_red_timer <= 0:
                self.in_all_red = False
                # Advance to next phase
                self.current_phase = (self.current_phase + 1) % 4
                self.phase_timer = self.green_splits[self.current_phase]
            return 0  # Extend (no action during all-red)
        
        # Green phase logic
        self.phase_timer -= 1
        
        if self.phase_timer <= 0:
            # Start yellow transition
            self.in_yellow = True
            self.yellow_timer = self.yellow_time
            return 0  # Extend during transition
        else:
            return 0  # Extend current green
    
    def reset(self):
        """Reset controller to initial state."""
        self.current_phase = 0
        self.phase_timer = self.green_splits[0]
        self.in_yellow = False
        self.in_all_red = False
        self.yellow_timer = 0
        self.all_red_timer = 0
        self.step_count = 0


# ============================================
# BASELINE EVALUATOR
# ============================================

class BaselineEvaluator:
    """
    Evaluates fixed-time controller on traffic scenarios.
    Mirrors the RL evaluation process for fair comparison.
    """
    
    def __init__(
        self,
        cycle_time: int = 120,
        green_splits: List[int] = None,
        verbose: bool = True
    ):
        """
        Initialize baseline evaluator.
        
        Args:
            cycle_time: Fixed cycle time in seconds
            green_splits: Green time allocation per phase
            verbose: Print progress
        """
        self.controller = FixedTimeController(
            cycle_time=cycle_time,
            green_splits=green_splits
        )
        self.verbose = verbose
        
        # Create evaluation environment
        self.env = TrafficEnv(
            max_steps=3600,
            saturation_flow_rate=0.53,
            lanes_per_direction=2,
            track_waiting_time=True,
        )
        
        if self.verbose:
            print(f"📊 Fixed-Time Controller Configuration:")
            print(f"   Cycle time: {cycle_time}s")
            print(f"   Green splits: {green_splits or [30, 10, 30, 10]}")
            print(f"   ✓ Baseline evaluator ready")
    
    def evaluate_single_episode(
        self,
        arrival_rates: Dict[str, float],
        seed: int = None
    ) -> Dict:
        """
        Run one episode with fixed-time control.
        
        Args:
            arrival_rates: Traffic arrival rates per direction
            seed: Random seed for reproducibility
        
        Returns:
            Episode metrics
        """
        obs = self.env.reset(arrival_rates=arrival_rates)
        self.controller.reset()
        
        done = False
        episode_reward = 0.0
        step_count = 0
        
        # Track metrics
        queue_history = []
        action_history = []
        phase_history = []
        
        while not done:
            # Get action from fixed-time controller
            action = self.controller.get_action(obs)
            
            # Execute action
            obs, reward, done, info = self.env.step(action)
            
            # Track
            episode_reward += reward
            step_count += 1
            queue_history.append(info['total_queue'])
            action_history.append(int(action))
            phase_history.append(int(info['phase']))
        
        # Get final metrics
        metrics = self.env.get_metrics()
        
        # Add episode data
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
        n_episodes: int = 5
    ) -> Dict:
        """
        Evaluate fixed-time control for one hour.
        
        Args:
            hour: Hour of day (0-23)
            arrival_rates_csv: Path to arrival rates CSV
            n_episodes: Number of episodes for averaging
        
        Returns:
            Aggregated metrics
        """
        if self.verbose:
            print(f"\n⏰ Evaluating Hour {hour:02d}:00 (Fixed-Time)")
        
        # Get arrival rates
        rates = get_hourly_rates(arrival_rates_csv, hour)
        if self.verbose:
            print(f"   Arrival rates: N={rates['north']:.2f}, S={rates['south']:.2f}, "
                  f"E={rates['east']:.2f}, W={rates['west']:.2f} veh/sec")
        
        # Run multiple episodes
        episode_results = []
        for ep in range(n_episodes):
            if self.verbose:
                print(f"   Episode {ep+1}/{n_episodes}...", end=' ')
            
            result = self.evaluate_single_episode(
                arrival_rates=rates,
                seed=hour * 100 + ep
            )
            episode_results.append(result)
            
            if self.verbose:
                print(f"Avg Queue: {result['avg_queue_length']:.2f}, "
                      f"Delay: {result['avg_vehicle_delay']:.2f}s, "
                      f"Reward: {result['episode_reward']:.2f}")
        
        # Aggregate
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
        Evaluate fixed-time control for all 24 hours.
        
        Args:
            arrival_rates_csv: Path to arrival rates CSV
            n_episodes_per_hour: Episodes per hour
            output_dir: Output directory
        
        Returns:
            DataFrame with results
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print("=" * 80)
        print("🚦 FULL DAY EVALUATION - FIXED-TIME BASELINE")
        print("=" * 80)
        print(f"Controller: Fixed-Time (120s cycle)")
        print(f"Episodes per hour: {n_episodes_per_hour}")
        print(f"Total episodes: {24 * n_episodes_per_hour}")
        print("=" * 80)
        
        all_results = []
        
        for hour in range(24):
            result = self.evaluate_hour(
                hour=hour,
                arrival_rates_csv=arrival_rates_csv,
                n_episodes=n_episodes_per_hour
            )
            all_results.append(result)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        
        # Save
        output_file = f"{output_dir}/baseline_evaluation.csv"
        df.to_csv(output_file, index=False)
        
        if self.verbose:
            print(f"\n💾 Results saved: {output_file}")
        
        # Generate summary
        self._generate_summary(df, output_dir)
        
        return df
    
    def _aggregate_episodes(self, episode_results: List[Dict]) -> Dict:
        """Aggregate metrics across episodes."""
        aggregated = {}
        
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
        
        aggregated['arrival_rates'] = episode_results[0]['arrival_rates']
        
        return aggregated
    
    def _generate_summary(self, df: pd.DataFrame, output_dir: str):
        """Generate summary report."""
        summary_file = f"{output_dir}/baseline_summary.txt"
        
        with open(summary_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("FIXED-TIME BASELINE EVALUATION SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Controller Type: Fixed-Time (Webster's Formula)\n")
            f.write(f"Cycle Time: {self.controller.cycle_time}s\n")
            f.write(f"Green Splits: {self.controller.green_splits}\n\n")
            
            f.write("OVERALL PERFORMANCE:\n")
            f.write("-" * 80 + "\n")
            f.write(f"  Average Queue Length:  {df['avg_queue_length_mean'].mean():.2f} ± {df['avg_queue_length_std'].mean():.2f} vehicles\n")
            f.write(f"  Average Vehicle Delay: {df['avg_vehicle_delay_mean'].mean():.2f} ± {df['avg_vehicle_delay_std'].mean():.2f} seconds\n")
            f.write(f"  Total Throughput:      {df['total_throughput_mean'].mean():.0f} ± {df['total_throughput_std'].mean():.0f} vehicles/hour\n")
            f.write(f"  Queue Imbalance:       {df['queue_imbalance_mean'].mean():.2f} ± {df['queue_imbalance_std'].mean():.2f}\n")
            f.write(f"  Average Reward:        {df['episode_reward_mean'].mean():.3f} ± {df['episode_reward_std'].mean():.3f}\n\n")
            
            f.write("PEAK HOUR PERFORMANCE:\n")
            f.write("-" * 80 + "\n")
            morning = df[df['hour'] == 8].iloc[0]
            f.write(f"  Morning Peak (08:00):\n")
            f.write(f"    Avg Queue: {morning['avg_queue_length_mean']:.2f} vehicles\n")
            f.write(f"    Avg Delay: {morning['avg_vehicle_delay_mean']:.2f} seconds\n\n")
            
            evening = df[df['hour'] == 18].iloc[0]
            f.write(f"  Evening Peak (18:00):\n")
            f.write(f"    Avg Queue: {evening['avg_queue_length_mean']:.2f} vehicles\n")
            f.write(f"    Avg Delay: {evening['avg_vehicle_delay_mean']:.2f} seconds\n\n")
            
            f.write("=" * 80 + "\n")
        
        if self.verbose:
            print(f"📄 Summary saved: {summary_file}")


# ============================================
# COMMAND-LINE INTERFACE
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate fixed-time baseline controller",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
        help="Output directory"
    )
    parser.add_argument(
        "--cycle",
        type=int,
        default=120,
        help="Cycle time in seconds"
    )
    parser.add_argument(
        "--splits",
        type=int,
        nargs=4,
        default=[30, 10, 30, 10],
        help="Green splits for 4 phases"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output"
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=None,
        help="Evaluate single hour only (0-23)"
    )
    
    args = parser.parse_args()
    
    # Validate
    if not os.path.exists(args.data):
        print(f"❌ Error: Data file not found: {args.data}")
        sys.exit(1)
    
    # Create evaluator
    evaluator = BaselineEvaluator(
        cycle_time=args.cycle,
        green_splits=args.splits,
        verbose=not args.quiet
    )
    
    # Run evaluation
    if hasattr(args, 'hour') and args.hour is not None:
        # Single hour evaluation
        result = evaluator.evaluate_hour(
            hour=args.hour,
            arrival_rates_csv=args.data,
            n_episodes=args.episodes
        )
        # Wrap single result in list for DataFrame compatibility
        results_df = pd.DataFrame([result])
        output_file = f"{args.output}/baseline_evaluation.csv"
        # Append if file exists, else write new? For now just overwrite or write single
        # Ideally we want a separate file or handle it, but compare.py expects this filename
        # Let's write just this hour to the CSV for comparison
        os.makedirs(args.output, exist_ok=True)
        results_df.to_csv(output_file, index=False)
        print(f"\n📊 Results for Hour {args.hour:02d}:00:")
        print(f"   Avg Queue: {result['avg_queue_length_mean']:.2f}")
    else:
        results_df = evaluator.evaluate_full_day(
            arrival_rates_csv=args.data,
            n_episodes_per_hour=args.episodes,
            output_dir=args.output
        )
    
    print("\n" + "=" * 80)
    print("✅ BASELINE EVALUATION COMPLETE!")
    print("=" * 80)
    print(f"\nResults saved to: {args.output}/")
    print(f"  - baseline_evaluation.csv  (detailed metrics)")
    print(f"  - baseline_summary.txt     (summary report)")
    print(f"\nNext: Run compare.py to compare RL vs Baseline")


if __name__ == "__main__":
    main()