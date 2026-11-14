cmake_minimum_required(VERSION 3.8)
project(continuum_carmy_motor_controller)

# The driver uses structured bindings and std::map::try_emplace.
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(continuum_msgs REQUIRED)

add_library(${PROJECT_NAME}_lib
  src/motor_cfg.cpp
)
set_target_properties(${PROJECT_NAME}_lib PROPERTIES
  OUTPUT_NAME ${PROJECT_NAME}
)
target_include_directories(${PROJECT_NAME}_lib
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

add_executable(rs_motor_ros2_node
  src/main.cpp
)
ament_target_dependencies(rs_motor_ros2_node rclcpp continuum_msgs)

target_link_libraries(rs_motor_ros2_node
  ${PROJECT_NAME}_lib
)

install(
  DIRECTORY include/
  DESTINATION include
)
install(
  TARGETS ${PROJECT_NAME}_lib rs_motor_ros2_node
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)
ament_export_include_directories(include)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_feedback_freshness
    test/test_feedback_freshness.cpp
  )
  target_include_directories(test_feedback_freshness PRIVATE include)
endif()

ament_package()
