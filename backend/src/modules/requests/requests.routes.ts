import { Router } from "express";

const router = Router();

router.get("/", (_req, res) => {
  res.json({ message: "Requests routes" });
});

export default router;
