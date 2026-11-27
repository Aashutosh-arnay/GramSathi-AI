
const mongoose = require("mongoose");

const conversationSchema = new mongoose.Schema(
  {
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },

    module: {
      type: String,
      enum: ["farmsathi", "nyayasathi"],
      required: true,
    },

    title: {
      type: String,
      trim: true,
      default: "New conversation",
    },
  },
  {
    timestamps: true,
  }
);

// Efficiently retrieve a user's conversations
conversationSchema.index({
  user: 1,
  updatedAt: -1,
});

const Conversation = mongoose.model(
  "Conversation",
  conversationSchema
);

module.exports = Conversation;
