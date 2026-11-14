#include <chrono>
#include <cmath>
#include <cstdint>
#include <map>
#include <memory>
#include <rclcpp/rclcpp.hpp>
#include <stdexcept>
#include <string>
#include <vector>

#include "continuum_carmy_motor_controller/motor_cfg.h"
#include "continuum_msgs/msg/motor_feedback.hpp"
#include "continuum_msgs/msg/motor_motion_control.hpp"

using MotorMotionControl = continuum_msgs::msg::MotorMotionControl;
using MotorFeedback = continuum_msgs::msg::MotorFeedback;

class MotorController : public rclcpp::Node
{
public:
  MotorController() : rclcpp::Node("motor_controller_node")
  {
    const auto hardware_enabled = declare_parameter<bool>("hardware_enabled", false);
    const auto can_interface = declare_parameter<std::string>("can_interface", "can0");
    const auto motor_ids = declare_parameter<std::vector<std::int64_t>>("motor_ids", { 1, 2, 3, 4 });
    const auto motor_types = declare_parameter<std::vector<std::int64_t>>("motor_types", { 5, 5, 5, 5 });
    command_timeout_sec_ = declare_parameter<double>("command_timeout_sec", 0.5);
    feedback_timeout_sec_ = declare_parameter<double>("feedback_timeout_sec", 0.5);

    if (can_interface.empty())
    {
      throw std::invalid_argument("can_interface must not be empty");
    }
    if (!std::isfinite(command_timeout_sec_) || command_timeout_sec_ <= 0.0)
    {
      throw std::invalid_argument("command_timeout_sec must be a finite positive value");
    }
    if (!std::isfinite(feedback_timeout_sec_) || feedback_timeout_sec_ <= 0.0)
    {
      throw std::invalid_argument("feedback_timeout_sec must be a finite positive value");
    }
    if (motor_ids.empty() || motor_ids.size() != motor_types.size())
    {
      throw std::invalid_argument("motor_ids and motor_types must have equal non-zero lengths");
    }

    std::map<std::uint8_t, int> configured_motors;
    for (std::size_t i = 0; i < motor_ids.size(); ++i)
    {
      if (motor_ids[i] < 1 || motor_ids[i] > 255)
      {
        throw std::invalid_argument("motor IDs must be in the range 1..255");
      }
      if (motor_types[i] < 0 || motor_types[i] > 6)
      {
        throw std::invalid_argument("motor types must be in the range 0..6");
      }
      if (!configured_motors.emplace(static_cast<std::uint8_t>(motor_ids[i]), static_cast<int>(motor_types[i])).second)
      {
        throw std::invalid_argument("motor IDs must be unique");
      }
    }

    hardware_enabled_ = hardware_enabled;
    motion_sub_ = create_subscription<MotorMotionControl>(
        "motion_control", 10, std::bind(&MotorController::motion_callback, this, std::placeholders::_1));
    feedback_pub_ = create_publisher<MotorFeedback>("motor_feedback", 10);

    if (!hardware_enabled_)
    {
      RCLCPP_WARN(get_logger(), "Hardware is disabled. Set hardware_enabled:=true only for "
                                "operator-supervised real hardware operation.");
      return;
    }

    for (const auto& [motor_id, motor_type] : configured_motors)
    {
      motors_.try_emplace(motor_id, can_interface, 0xFF, motor_id, motor_type);
    }

    for (auto& [motor_id, motor] : motors_)
    {
      (void)motor_id;
      motor.Get_RobStrite_Motor_parameter(0x7005);
      motor.enable_motor();
    }

    publish_timer_ = create_wall_timer(std::chrono::milliseconds(20), std::bind(&MotorController::hold_position, this));
  }

  ~MotorController() override
  {
    if (hardware_enabled_)
    {
      for (auto& [motor_id, motor] : motors_)
      {
        (void)motor_id;
        motor.Disenable_Motor(0);
      }
    }
  }

  void motion_callback(const MotorMotionControl::SharedPtr msg)
  {
    if (!hardware_enabled_)
    {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000, "Ignoring motor command because hardware is disabled");
      return;
    }
    const auto motor = motors_.find(msg->motor_id);
    if (motor == motors_.end())
    {
      RCLCPP_WARN(get_logger(), "Unknown motor ID %u", msg->motor_id);
      return;
    }
    if (!std::isfinite(msg->position) || !std::isfinite(msg->velocity) || !std::isfinite(msg->kp) ||
        !std::isfinite(msg->kd) || !std::isfinite(msg->torque) || msg->kp < 0.0 || msg->kd < 0.0)
    {
      RCLCPP_WARN(get_logger(), "Ignoring invalid command for motor %u", msg->motor_id);
      return;
    }

    target_position_[msg->motor_id] = msg->position;
    target_velocity_[msg->motor_id] = msg->velocity;
    target_kp_[msg->motor_id] = msg->kp;
    target_kd_[msg->motor_id] = msg->kd;
    target_torque_[msg->motor_id] = msg->torque;
    last_command_time_[msg->motor_id] = std::chrono::steady_clock::now();
    has_target_[msg->motor_id] = true;
    stale_reported_[msg->motor_id] = false;
    apply_target(msg->motor_id);
  }

private:
  void apply_target(std::uint8_t motor_id)
  {
    const auto motor = motors_.find(motor_id);
    if (motor == motors_.end() || !has_target_[motor_id])
    {
      return;
    }

    const auto elapsed = std::chrono::steady_clock::now() - last_command_time_[motor_id];
    if (elapsed > std::chrono::duration<double>(command_timeout_sec_))
    {
      if (!stale_reported_[motor_id])
      {
        RCLCPP_WARN(get_logger(),
                    "Command for motor %u expired; no further motion command will be "
                    "sent until a fresh command arrives. The physical motor is not "
                    "known to be stopped.",
                    motor_id);
        stale_reported_[motor_id] = true;
      }
      return;
    }

    motor->second.send_motion_command(target_torque_[motor_id], target_position_[motor_id], target_velocity_[motor_id],
                                      target_kp_[motor_id], target_kd_[motor_id]);
  }

  void hold_position()
  {
    for (const auto& [motor_id, motor] : motors_)
    {
      (void)motor;
      apply_target(motor_id);
    }
    publish_feedback();
  }

  void publish_feedback()
  {
    for (auto& [motor_id, motor] : motors_)
    {
      MotorFeedback feedback;
      feedback.motor_id = motor_id;

      try
      {
        motor.receive_status_frame();
      }
      catch (const std::exception& error)
      {
        RCLCPP_WARN(get_logger(), "Feedback read failed for motor %u: %s", motor_id, error.what());
      }

      const auto [position, velocity, torque, temperature] = motor.return_data_pvtt();
      feedback.connected = motor.has_fresh_feedback(std::chrono::duration<double>(feedback_timeout_sec_));
      feedback.position = position;
      feedback.velocity = velocity;
      feedback.torque = torque;
      feedback.temperature = temperature;
      feedback_pub_->publish(feedback);
    }
  }

  bool hardware_enabled_{ false };
  double command_timeout_sec_{ 0.5 };
  double feedback_timeout_sec_{ 0.5 };
  rclcpp::Subscription<MotorMotionControl>::SharedPtr motion_sub_;
  rclcpp::Publisher<MotorFeedback>::SharedPtr feedback_pub_;
  rclcpp::TimerBase::SharedPtr publish_timer_;
  std::map<std::uint8_t, RobStrideMotor> motors_;
  std::map<std::uint8_t, double> target_position_;
  std::map<std::uint8_t, double> target_velocity_;
  std::map<std::uint8_t, double> target_kp_;
  std::map<std::uint8_t, double> target_kd_;
  std::map<std::uint8_t, double> target_torque_;
  std::map<std::uint8_t, bool> has_target_;
  std::map<std::uint8_t, bool> stale_reported_;
  std::map<std::uint8_t, std::chrono::steady_clock::time_point> last_command_time_;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  try
  {
    auto controller = std::make_shared<MotorController>();
    rclcpp::spin(controller);
  }
  catch (const std::exception& error)
  {
    RCLCPP_FATAL(rclcpp::get_logger("motor_controller_node"), "Motor controller failed: %s", error.what());
    rclcpp::shutdown();
    return 1;
  }
  rclcpp::shutdown();
  return 0;
}
