#!/usr/bin/env python3

import sapien.core as sapien
from sapien.utils.viewer import Viewer

import mplib
from mplib import Pose


class DemoSetup:
    """
    This class is the super class to abstract away some of the setups for the demos.
    You will need to install Sapien via `pip install sapien` for this to work
    if you want to use the viewer.
    """

    def __init__(self):
        """Nothing to do"""
        pass

    def setup_scene(self, **kwargs):
        """This is the Sapien simulator setup and has nothing to do with mplib"""
        # declare sapien sim
        self.engine = sapien.Engine()
        # declare sapien renderer
        self.renderer = sapien.SapienRenderer()
        # give renderer to sapien sim
        self.engine.set_renderer(self.renderer)

        # declare sapien scene
        scene_config = sapien.SceneConfig()
        self.scene = self.engine.create_scene(scene_config)
        # set simulation timestep
        self.scene.set_timestep(kwargs.get("timestep", 1 / 240))
        # add ground to scene
        self.scene.add_ground(kwargs.get("ground_height", 0))
        # set default physical material
        self.scene.default_physical_material = self.scene.create_physical_material(
            kwargs.get("static_friction", 1),
            kwargs.get("dynamic_friction", 1),
            kwargs.get("restitution", 0),
        )
        # give some white ambient light of moderate intensity
        self.scene.set_ambient_light(kwargs.get("ambient_light", [0.5, 0.5, 0.5]))
        # default enable shadow unless specified otherwise
        shadow = kwargs.get("shadow", True)
        # default spotlight angle and intensity
        direction_lights = kwargs.get(
            "direction_lights", [[[0, 1, -1], [0.5, 0.5, 0.5]]]
        )
        for direction_light in direction_lights:
            self.scene.add_directional_light(
                direction_light[0], direction_light[1], shadow=shadow
            )
        # default point lights position and intensity
        point_lights = kwargs.get(
            "point_lights",
            [[[1, 2, 2], [1, 1, 1]], [[1, -2, 2], [1, 1, 1]], [[-1, 0, 1], [1, 1, 1]]],
        )
        for point_light in point_lights:
            self.scene.add_point_light(point_light[0], point_light[1], shadow=shadow)

        # initialize viewer with camera position and orientation
        self.viewer = Viewer(self.renderer)
        self.viewer.set_scene(self.scene)
        self.viewer.set_camera_xyz(
            x=kwargs.get("camera_xyz_x", 1.2),
            y=kwargs.get("camera_xyz_y", 0.25),
            z=kwargs.get("camera_xyz_z", 0.4),
        )
        self.viewer.set_camera_rpy(
            r=kwargs.get("camera_rpy_r", 0),
            p=kwargs.get("camera_rpy_p", -0.4),
            y=kwargs.get("camera_rpy_y", 2.7),
        )

    def load_robot(self, **kwargs):
        """
        This function loads a robot from a URDF file into the Sapien Scene.
        Note that does mean that setup_scene() must be called before this function.
        """
        loader: sapien.URDFLoader = self.scene.create_urdf_loader()
        loader.fix_root_link = True
        self.robot: sapien.Articulation = loader.load(
            kwargs.get("urdf_path", "./data/panda/panda.urdf")
        )
        self.robot.set_root_pose(
            sapien.Pose(
                kwargs.get("robot_origin_xyz", [0, 0, 0]),
                kwargs.get("robot_origin_quat", [1, 0, 0, 0]),
            )
        )
        self.active_joints = self.robot.get_active_joints()
        for joint in self.active_joints:
            joint.set_drive_property(
                stiffness=kwargs.get("joint_stiffness", 1000),
                damping=kwargs.get("joint_damping", 200),
            )

    def setup_planner(self, **kwargs):
        """
        Create an mplib planner using the default robot.
        See planner.py for more details on the arguments.
        """
        self.planner = mplib.Planner(
            urdf=kwargs.get("urdf_path", "./data/panda/panda.urdf"),
            srdf=kwargs.get("srdf_path", "./data/panda/panda.srdf"),
            move_group=kwargs.get("move_group", "panda_hand"),
        )

    # follow path ankor
    def follow_path(self, result):
        """Helper function to follow a path generated by the planner"""
        # number of waypoints in the path
        n_step = result["position"].shape[0]
        # this makes sure the robot stays neutrally boyant instead of sagging
        # under gravity
        for i in range(n_step):
            qf = self.robot.compute_passive_force(
                gravity=True, coriolis_and_centrifugal=True
            )
            self.robot.set_qf(qf)
            # set the joint positions and velocities for move group joints only.
            # The others are not the responsibility of the planner
            for j in range(len(self.planner.move_group_joint_indices)):
                self.active_joints[j].set_drive_target(result["position"][i][j])
                self.active_joints[j].set_drive_velocity_target(
                    result["velocity"][i][j]
                )
            # simulation step
            self.scene.step()
            # render every 4 simulation steps to make it faster
            if i % 4 == 0:
                self.scene.update_render()
                self.viewer.render()

    # follow path ankor end
    def set_gripper(self, pos):
        """
        Helper function to activate gripper joints
        Args:
            pos: position of the gripper joint in real number
        """
        # The following two lines are particular to the panda robot
        for joint in self.active_joints[-2:]:
            joint.set_drive_target(pos)
        # 100 steps is plenty to reach the target position
        for i in range(100):
            qf = self.robot.compute_passive_force(
                gravity=True, coriolis_and_centrifugal=True
            )
            self.robot.set_qf(qf)
            self.scene.step()
            if i % 4 == 0:
                self.scene.update_render()
                self.viewer.render()

    def open_gripper(self):
        self.set_gripper(0.4)

    def close_gripper(self):
        self.set_gripper(0)

    def move_to_pose_with_RRTConnect(self, pose: Pose):
        """
        Plan and follow a path to a pose using RRTConnect

        Args:
            pose: mplib.Pose
        """
        # result is a dictionary with keys 'status', 'time', 'position', 'velocity',
        # 'acceleration', 'duration'
        # plan_qpos_to_pose ankor
        print("plan_qpos_to_pose")
        result = self.planner.plan_qpos_to_pose(
            pose, self.robot.get_qpos(), time_step=1 / 250
        )
        # plan_qpos_to_pose ankor end
        if result["status"] != "Success":
            print(result["status"])
            return -1
        # do nothing if the planning fails; follow the path if the planning succeeds
        self.follow_path(result)
        return 0

    def move_to_pose_with_screw(self, pose):
        """
        Interpolative planning with screw motion.
        Will not avoid collision and will fail if the path contains collision.
        """
        result = self.planner.plan_screw(
            pose,
            self.robot.get_qpos(),
            time_step=1 / 250,
        )
        if result["status"] == "Success":
            self.follow_path(result)
            return 0
        else:
            # fall back to RRTConnect if the screw motion fails (say contains collision)
            return self.move_to_pose_with_RRTConnect(pose)

    def move_to_pose(self, pose, with_screw=True):
        """API to multiplex between the two planning methods"""
        if with_screw:
            return self.move_to_pose_with_screw(pose)
        else:
            return self.move_to_pose_with_RRTConnect(pose)
