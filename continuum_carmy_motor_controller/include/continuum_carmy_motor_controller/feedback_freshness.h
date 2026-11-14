#pragma once

#include <chrono>
#include <optional>

class FeedbackFreshness
{
public:
  using Clock = std::chrono::steady_clock;

  void mark_received(Clock::time_point received_at = Clock::now())
  {
    last_received_ = received_at;
  }

  bool is_fresh(std::chrono::duration<double> timeout, Clock::time_point now = Clock::now()) const
  {
    return timeout.count() > 0.0 && last_received_.has_value() && now >= *last_received_ &&
           now - *last_received_ <= timeout;
  }

private:
  std::optional<Clock::time_point> last_received_;
};