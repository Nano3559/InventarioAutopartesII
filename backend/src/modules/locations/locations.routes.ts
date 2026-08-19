import { Router } from "express";

const router = Router();

router.get("/", (_req, res) => {
  res.json({ message: "Locations routes" });
});

export default router;
