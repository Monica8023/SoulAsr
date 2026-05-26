import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "dashboard",
    component: () => import("../views/Dashboard.vue"),
    meta: {
      title: "系统仪表盘",
    },
  },
  {
    path: "/workbench",
    name: "workbench",
    component: () => import("../views/DebugWorkbench.vue"),
    meta: {
      title: "ASR 调试工作台",
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
