import { configureStore } from '@reduxjs/toolkit';
import authSlice from './authSlice';
import chatSlice from './chatSlice';
import dashboardSlice from './dashboardSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    chat: chatSlice,
    dashboard: dashboardSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;