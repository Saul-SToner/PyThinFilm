import * as THREE from "three";

export class RendererLifecycle {
  constructor(container) {
    this.container = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(container.clientWidth || 800, container.clientHeight || 600);
    if (container && container.appendChild) {
      container.appendChild(this.renderer.domElement);
    }

    this.animationFrameId = null;
    this.isRendering = false;

    // Instrumentation metrics for testing
    this.contextLossCount = 0;
    this.rendererDisposeCount = 0;
    this.disposeCount = 0;
    this.animationCancelCount = 0;
  }

  startLoop(renderCallback) {
    if (this.isRendering) return;
    this.isRendering = true;
    const loop = (timestamp) => {
      if (!this.isRendering) return;
      renderCallback(timestamp);
      this.animationFrameId = requestAnimationFrame(loop);
    };
    this.animationFrameId = requestAnimationFrame(loop);
  }

  stopLoop() {
    this.isRendering = false;
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
      this.animationCancelCount += 1;
    }
  }

  onResize() {
    const width = this.container ? this.container.clientWidth : 0;
    const height = this.container ? this.container.clientHeight : 0;
    if (width > 0 && height > 0 && this.renderer) {
      this.renderer.setSize(width, height);
    }
  }

  getDomElement() {
    return this.renderer ? this.renderer.domElement : null;
  }

  getRenderer() {
    return this.renderer;
  }

  // Full Application Teardown (Only called when unmounting the whole app)
  teardown() {
    this.stopLoop();
    if (this.renderer) {
      this.renderer.forceContextLoss();
      this.contextLossCount += 1;
      this.renderer.dispose();
      this.rendererDisposeCount += 1;
      this.disposeCount += 1;
      if (this.renderer.domElement && this.renderer.domElement.parentNode) {
        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
      }
      this.renderer = null;
    }
  }
}
