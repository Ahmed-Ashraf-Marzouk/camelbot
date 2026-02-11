import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    headless: false,   // live preview
    video: 'on',       // record video
  },
});
