import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir:'./browser-tests',timeout:60000,workers:1,
  use:{baseURL:'http://localhost:5173',channel:'chrome',headless:true,viewport:{width:1440,height:960},screenshot:'only-on-failure'},
  webServer:{command:'npm.cmd run dev',url:'http://localhost:5173',reuseExistingServer:true,timeout:60000},
});
