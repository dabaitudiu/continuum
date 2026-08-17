import '@testing-library/jest-dom/vitest'

class ResizeObserverStub implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}
  disconnect(): void {}
  observe(target: Element): void {
    this.callback(
      [
        {
          target,
          contentRect: target.getBoundingClientRect(),
          borderBoxSize: [],
          contentBoxSize: [],
          devicePixelContentBoxSize: [],
        },
      ],
      this,
    )
  }
  unobserve(): void {}
}

globalThis.ResizeObserver = ResizeObserverStub

class DOMMatrixReadOnlyStub {
  readonly m22 = 1
}

Object.defineProperty(window, 'DOMMatrixReadOnly', {
  value: DOMMatrixReadOnlyStub,
  writable: true,
})

Object.defineProperties(HTMLElement.prototype, {
  offsetWidth: {
    configurable: true,
    get() {
      return this.classList.contains('runtime-node') ? 204 : 1024
    },
  },
  offsetHeight: {
    configurable: true,
    get() {
      return this.classList.contains('runtime-node') ? 88 : 640
    },
  },
})

HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
  const width = this.classList.contains('runtime-node') ? 204 : 1024
  const height = this.classList.contains('runtime-node') ? 88 : 640
  return {
    x: 0,
    y: 0,
    width,
    height,
    top: 0,
    right: width,
    bottom: height,
    left: 0,
    toJSON: () => ({}),
  }
}
