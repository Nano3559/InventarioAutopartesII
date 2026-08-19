import { Router } from "express";

const router = Router();

router.get("/", (_req, res) => {
  res.json({ message: "Prices routes" });
});

export default router;
