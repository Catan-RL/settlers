import os
import time
import numpy as np
import random
import torch

from collections import deque

import RL.ppo.utils as utils

from RL.ppo.arguments import get_args
from RL.ppo.game_manager import make_game_manager
from RL.ppo.vec_gather_experience import SubProcGameManager
from RL.models.build_agent_model import build_agent_model
from RL.ppo.process_batch import BatchProcessor
# from RL.ppo.update_opponent_policies import update_opponent_policies
# from RL.ppo.run_evaluation_protocol import run_evaluation_protocol
from RL.ppo.ppo import PPO

def main():
    args = get_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    if args.cuda and torch.cuda.is_available() and args.cuda_deterministic:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    experiment_dir = "RL/results"
    os.makedirs(experiment_dir, exist_ok=True)

    torch.set_num_threads(1)
    device = torch.device("cuda:0" if args.cuda else "cpu")

    rollout_manager_fns = [
        make_game_manager(args.num_envs_per_process, args.num_steps) for _ in range(args.num_processes)
    ]
    rollout_manager = SubProcGameManager(rollout_manager_fns)
    rollout_manager.seed([10])

    if args.load_from_checkpoint:
        central_policy, earlier_policies, eval_logs, start_update = torch.load("RL/results/"+args.load_file_path)
        update_opponent_policies(earlier_policies, rollout_manager)
    else:
        central_policy = build_agent_model(device=device)
        earlier_policies = deque(maxlen=args.num_policies_to_store)
        earlier_policies.append(central_policy.state_dict())
        start_update = 0
        eval_logs = []

    rollout_storage = BatchProcessor(args, central_policy.lstm_size, device=device)

    agent = PPO(central_policy, args)

    start_time = time.time()
    num_updates = int(args.total_env_steps) // args.num_steps // (args.num_processes * args.num_envs_per_process)
    steps_per_update = int(args.num_steps * args.num_processes * args.num_envs_per_process)

    for update_num in range(start_update, num_updates):

        if args.use_linear_lr_decay:
            utils.update_linear_schedule(agent.optimiser, update_num, num_updates, args.lr)

        rollouts = rollout_manager.gather_rollouts()
        rollout_storage.process_rollouts(rollouts)

        val_loss, action_loss, entropy_loss = agent.update(rollout_storage)

        if update_num % args.add_policy_every == 0:
            earlier_policies.append(central_policy.state_dict())

        if update_num % args.update_opponents_policies_every == 0:
            # update_opponent_policies(earlier_policies, rollout_manager)
            rollout_manager.reset()

        if update_num % args.eval_every == 0:
            # log, print_summary = run_evaluation_protocol(central_policy, earlier_policies, args)
            eval_logs.append(log)

            t_current = time.time()
            print("Updates complete: {}. Total policy steps: {}. Number of games complete: {}. Total elapsed time: {} hours.".format(
                update_num, steps_per_update * num_updates, rollout_storage.games_complete, (t_current - start_time)/3600.0
            ))
            print(print_summary)

            torch.save((central_policy, earlier_policies, eval_logs, update_num), "RL/results/"+args.expt_id)

if __name__ == "__main__":
    main()