export class AnimationController {
  constructor() {
    this.isPlaying = true;
    this.time = 0;
    this.speed = 1.0;
    this.caseUpdateSubscriptionRemovalCount = 0;
  }

  notifyCaseUnsubscribed() {
    this.caseUpdateSubscriptionRemovalCount += 1;
  }

  togglePlayPause() {
    this.isPlaying = !this.isPlaying;
    return this.isPlaying;
  }

  update(deltaSeconds) {
    if (this.isPlaying) {
      this.time += deltaSeconds * this.speed;
    }
    return this.time;
  }

  reset() {
    this.time = 0;
    this.isPlaying = true;
  }

  setSpeed(speed) {
    this.speed = Math.max(0.1, Math.min(5.0, Number(speed) || 1.0));
  }
}

