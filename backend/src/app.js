
const express = require("express");
const cors = require("cors");

const authRoutes = require("./routes/authRoutes");
const conversationRoutes = require("./routes/conversationRoutes");
const farmSathiRoutes = require("./routes/farmsathi.routes");
const nyayaSathiRoutes = require("./routes/nyayasathi.routes");

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Root route
app.get("/", (req, res) => {
  res.send("GramSathi AI API running");
});

// Existing routes
app.use("/api/auth", authRoutes);
app.use("/api/conversations", conversationRoutes);

// AI routes
app.use("/api/farmsathi", farmSathiRoutes);
app.use("/api/nyayasathi", nyayaSathiRoutes);

module.exports = app;
