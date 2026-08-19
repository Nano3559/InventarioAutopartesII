import { Router } from "express";

const router = Router();

router.get("/", (_req, res) => {
  res.json({ message: "Sales routes" });
});

export default router;
