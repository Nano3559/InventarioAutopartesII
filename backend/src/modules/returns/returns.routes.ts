import { Router } from "express";

const router = Router();

router.get("/", (_req, res) => {
  res.json({ message: "Returns routes" });
});

export default router;
