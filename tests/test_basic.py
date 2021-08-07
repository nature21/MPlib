from mplib import Planner
import numpy as np


def test():
    planner = Planner(
        urdf="data/panda/panda.urdf",
        srdf="data/panda/panda.srdf",
        user_link_names=[
            "panda_link0",
            "panda_link1",
            "panda_link2",
            "panda_link3",
            "panda_link4",
            "panda_link5",
            "panda_link6",
            "panda_link7",
            "panda_link8",
            "panda_hand",
            "panda_leftfinger",
            "panda_rightfinger",
        ],
        user_joint_names=[
            "panda_joint1",
            "panda_joint2",
            "panda_joint3",
            "panda_joint4",
            "panda_joint5",
            "panda_joint6",
            "panda_joint7",
            "panda_finger_joint1",
            "panda_finger_joint2",
        ],
        move_group="panda_link5",
        joint_vel_limits=np.ones(7),
        joint_acc_limits=np.ones(7),
    )
    pose = [0.4, 0.3, 0.12, 0, 1, 0, 0]
    qpos = np.array([0, 0.2, 0, -2.6, 0, 3.0, 0.8, 0, 0])
    result = planner.plan(pose, qpos, time_step=1 / 250)


if __name__ == "__main__":
    test()
