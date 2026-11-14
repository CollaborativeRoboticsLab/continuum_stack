#include <gtest/gtest.h>

#include <chrono>

#include "continuum_carmy_motor_controller/feedback_freshness.h"

TEST(FeedbackFreshness, StartsStaleAndExpiresAfterTimeout)
{
  FeedbackFreshness freshness;
  const auto start = FeedbackFreshness::Clock::time_point{};
  const auto timeout = std::chrono::duration<double>(0.5);

  EXPECT_FALSE(freshness.is_fresh(timeout, start));

  freshness.mark_received(start);
  EXPECT_TRUE(freshness.is_fresh(timeout, start));
  EXPECT_TRUE(freshness.is_fresh(timeout, start + std::chrono::milliseconds(500)));
  EXPECT_FALSE(freshness.is_fresh(timeout, start + std::chrono::milliseconds(501)));
}

TEST(FeedbackFreshness, NewFeedbackRestoresFreshState)
{
  FeedbackFreshness freshness;
  const auto start = FeedbackFreshness::Clock::time_point{};
  const auto timeout = std::chrono::duration<double>(0.5);

  freshness.mark_received(start);
  const auto recovered_at = start + std::chrono::seconds(2);
  EXPECT_FALSE(freshness.is_fresh(timeout, recovered_at));

  freshness.mark_received(recovered_at);
  EXPECT_TRUE(freshness.is_fresh(timeout, recovered_at));
}