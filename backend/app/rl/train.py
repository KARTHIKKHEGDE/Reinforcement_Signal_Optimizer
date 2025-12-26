"""
RL Model Training Script
Train PPO agent for traffic signal control
"""
from stable_baselines3 import PPO, DQN
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
import os
from app.rl.env import create_training_env
from app.config import settings


def train_ppo_model(
    total_timesteps: int = None,
    save_path: str = None,
    tensorboard_log: str = "./tensorboard_logs/"
):
    """
    Train PPO model for traffic signal control
    
    Args:
        total_timesteps: Number of training timesteps
        save_path: Path to save trained model
        tensorboard_log: Path for tensorboard logs
    """
    if total_timesteps is None:
        total_timesteps = settings.TRAINING_TIMESTEPS
    
    if save_path is None:
        save_path = settings.MODEL_PATH
    
    print("Creating training environment...")
    env = create_training_env()
    env = Monitor(env)
    
    print("Initializing PPO model...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        tensorboard_log=tensorboard_log
    )
    
    # Create callbacks
    os.makedirs("models/checkpoints", exist_ok=True)
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path="models/checkpoints/",
        name_prefix="ppo_traffic"
    )
    
    print(f"Starting training for {total_timesteps} timesteps...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=checkpoint_callback,
        progress_bar=True
    )
    
    # Save final model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save(save_path)
    print(f"Model saved to {save_path}")
    
    env.close()
    return model


def train_dqn_model(
    total_timesteps: int = None,
    save_path: str = "models/dqn_model.zip",
    tensorboard_log: str = "./tensorboard_logs/"
):
    """
    Train DQN model for traffic signal control
    
    Args:
        total_timesteps: Number of training timesteps
        save_path: Path to save trained model
        tensorboard_log: Path for tensorboard logs
    """
    if total_timesteps is None:
        total_timesteps = settings.TRAINING_TIMESTEPS
    
    print("Creating training environment...")
    env = create_training_env()
    env = Monitor(env)
    
    print("Initializing DQN model...")
    model = DQN(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=1e-4,
        buffer_size=50000,
        learning_starts=1000,
        batch_size=32,
        gamma=0.99,
        target_update_interval=1000,
        tensorboard_log=tensorboard_log
    )
    
    # Create callbacks
    os.makedirs("models/checkpoints", exist_ok=True)
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path="models/checkpoints/",
        name_prefix="dqn_traffic"
    )
    
    print(f"Starting training for {total_timesteps} timesteps...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=checkpoint_callback,
        progress_bar=True
    )
    
    # Save final model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save(save_path)
    print(f"Model saved to {save_path}")
    
    env.close()
    return model


if __name__ == "__main__":
    # Train PPO model
    print("=" * 50)
    print("Training PPO Model")
    print("=" * 50)
    train_ppo_model()
    
    # Optionally train DQN
    # print("\n" + "=" * 50)
    # print("Training DQN Model")
    # print("=" * 50)
    # train_dqn_model()
