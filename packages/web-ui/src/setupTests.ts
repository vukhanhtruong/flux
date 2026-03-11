/// <reference types="vitest/globals" />
import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// Mock ResizeObserver which is often used by charting libraries and isn't available in jsdom
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock fetch globally
globalThis.fetch = vi.fn();
