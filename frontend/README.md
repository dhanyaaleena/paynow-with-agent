# Agent Decision Viewer — Lite

A modern React/Next.js frontend for the PayNow + Agent Assist payment decision system. This dashboard provides an intuitive interface for submitting payment decisions and viewing AI agent analysis results.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- Backend API running on `http://localhost:8000`

### Installation & Running

```bash
# 1. Install dependencies
npm install

# 2. Set environment variables (create .env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=test-api-key

# 3. Start development server
npm run dev

# 4. Open http://localhost:3000
```

**That's it!** The app will be running in 3 commands.

## ✨ Features

### Must-Have UI (All Implemented)
1. **Submit Form**: Amount, payee, customerId → calls `/api/decide`
2. **Results Table**: Last 20 decisions with decision, amount, masked customerId, latency
3. **Details Drawer**: Collapsible reasons + Agent Trace for each row

### Non-Negotiables (All Met)
- **State Management**: Zustand store with clean actions and selectors
- **Loading/Empty/Error States**: Skeleton states, "no data" messages, error handling
- **Accessibility**: Labeled inputs, keyboard navigation, focus management, ARIA attributes
- **Security Boundary**: Customer IDs masked as `c_***123`, no PII exposure
- **Testing**: Jest + RTL test covering drawer expansion and accessibility
- **Performance**: Memoized row rendering with React.memo

## Architecture

### State Management
- **Zustand Store**: Lightweight, no boilerplate, TypeScript-first
- **Actions**: Form updates, API calls, UI state management
- **Selectors**: Reactive state updates with minimal re-renders

### Component Structure
```
src/
├── components/
│   ├── PaymentForm.tsx      # Form with validation & submission
│   ├── DecisionTable.tsx    # Table with memoized rows
│   └── DecisionDrawer.tsx   # Collapsible detail view
├── store/
│   └── decisionStore.ts     # Zustand store
├── services/
│   └── api.ts              # API calls with error handling
└── types/
    └── api.ts              # TypeScript interfaces
```

### API Integration
- **POST `/api/decide`**: Submit new payment decisions
- **GET `/api/decide`**: Fetch recent decisions for table
- **Error Handling**: Graceful fallbacks, user-friendly messages
- **Type Safety**: Full TypeScript coverage for API responses

## 🧪 Testing

```bash
# Run tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

### Test Coverage
- **DecisionDrawer**: Accessibility, expansion/collapse, keyboard navigation
- **Component Integration**: Store integration, error handling
- **Accessibility**: ARIA attributes, keyboard support, screen reader compatibility

## 🎨 UI/UX Features

### Form Experience
- **Real-time Validation**: Immediate feedback on input errors
- **Auto-generation**: Idempotency keys generated automatically
- **Smart Defaults**: USD currency, helpful placeholders
- **Accessibility**: Proper labels, help text, error descriptions

### Table Experience
- **Interactive Rows**: Click to view details, hover effects
- **Visual Indicators**: Color-coded decisions, icons for status
- **Responsive Design**: Horizontal scroll on small screens
- **Performance**: Memoized row components, efficient re-renders

### Drawer Experience
- **Collapsible Sections**: Reasons (open by default), Agent Trace (collapsed)
- **Rich Content**: Formatted amounts, dates, step-by-step trace
- **Keyboard Navigation**: Tab order, Enter/Space activation
- **Smooth Animations**: Headless UI transitions, focus management

## 🔧 Performance Optimizations

### Memoization Strategy
- **Row Components**: `React.memo` prevents unnecessary re-renders
- **Sorted Data**: `useMemo` for expensive sorting operations
- **Store Updates**: Selective state updates, minimal re-renders

### Why Memoized Rows?
- **Large Tables**: 20+ rows could cause performance issues
- **Frequent Updates**: API calls, form submissions trigger re-renders
- **User Experience**: Smooth scrolling, responsive interactions
- **Memory Efficiency**: Prevents unnecessary component recreation

## ♿ Accessibility Features

### Screen Reader Support
- **ARIA Labels**: Proper roles, states, and descriptions
- **Semantic HTML**: Table headers, form labels, button descriptions
- **Focus Management**: Logical tab order, visible focus indicators

### Keyboard Navigation
- **Form Controls**: Tab navigation, Enter submission
- **Table Interaction**: Space/Enter to open drawer
- **Drawer Controls**: Escape to close, focus trapping
- **Collapsible Sections**: Enter/Space to expand/collapse

### Visual Accessibility
- **Color Contrast**: WCAG AA compliant color schemes
- **Status Indicators**: Icons + colors + text for decisions
- **Error States**: Clear visual feedback, descriptive messages

## 🚨 Error Handling

### User Experience
- **Graceful Degradation**: App continues working despite errors
- **Clear Messages**: User-friendly error descriptions
- **Auto-dismissal**: Errors clear after 5 seconds
- **Retry Options**: Form validation, resubmission support

### Error Types
- **Validation Errors**: Form field requirements, amount validation
- **API Errors**: Network issues, server errors, rate limiting
- **State Errors**: Store corruption, component failures

## 🔒 Security Features

### PII Protection
- **Customer ID Masking**: `c_123` → `c_***123`
- **No Raw Data**: All sensitive information is masked
- **Client-side Validation**: Prevents unnecessary API calls

### API Security
- **API Key Authentication**: Required for all endpoints
- **Input Validation**: Server-side and client-side validation
- **Error Sanitization**: No sensitive data in error messages

## 📱 Responsive Design

### Breakpoint Strategy
- **Mobile First**: Optimized for small screens
- **Grid Layout**: Responsive columns, stack on mobile
- **Touch Friendly**: Appropriate button sizes, spacing

### Layout Adaptations
- **Desktop**: Two-column layout (form + table)
- **Tablet**: Stacked layout with full-width components
- **Mobile**: Single column, optimized table scrolling

## 🚀 Deployment

### Build Process
```bash
# Production build
npm run build

# Start production server
npm start
```

### Environment Variables
```bash
# Required
NEXT_PUBLIC_API_URL=https://your-api.com
NEXT_PUBLIC_API_KEY=your-api-key

# Optional
NODE_ENV=production
```

## 🔄 Trade-offs & Decisions

### 1. **State Management: Zustand vs Redux**
- **Chosen**: Zustand
- **Why**: Zero boilerplate, TypeScript-first, lightweight
- **Trade-off**: Less ecosystem, but simpler for this use case

### 2. **Styling: Tailwind vs CSS Modules**
- **Chosen**: Tailwind CSS
- **Why**: Rapid development, consistent design system
- **Trade-off**: Larger bundle, but faster development

### 3. **Testing: Jest vs Vitest**
- **Chosen**: Jest
- **Why**: Better React integration, mature ecosystem
- **Trade-off**: Slower than Vitest, but more stable

### 4. **Performance: Memoization vs Virtual Scrolling**
- **Chosen**: React.memo
- **Why**: Simple, effective for 20 rows
- **Trade-off**: Not scalable to 1000+ rows, but sufficient for requirements

### 5. **Accessibility: Custom vs Headless UI**
- **Chosen**: Headless UI
- **Why**: Battle-tested accessibility, less custom code
- **Trade-off**: Less customization, but better accessibility out-of-the-box

## 🎯 Future Enhancements

### Potential Improvements
- **Real-time Updates**: WebSocket integration for live decisions
- **Advanced Filtering**: Search, date ranges, decision types
- **Export Functionality**: CSV/PDF download of decision data
- **Dark Mode**: Theme switching with system preference detection
- **Mobile App**: React Native or PWA for mobile users

### Scalability Considerations
- **Virtual Scrolling**: For tables with 1000+ rows
- **Pagination**: Server-side pagination for large datasets
- **Caching**: React Query for API response caching
- **Offline Support**: Service worker for offline functionality

## 🤝 Contributing

### Development Workflow
1. **Feature Branch**: Create branch from `main`
2. **Development**: Implement with tests
3. **Testing**: Run full test suite
4. **Accessibility**: Verify with screen readers
5. **Performance**: Check bundle size and render performance
6. **Review**: Submit PR with clear description

### Code Standards
- **TypeScript**: Strict mode, no `any` types
- **ESLint**: Next.js recommended rules
- **Prettier**: Consistent code formatting
- **Testing**: 80%+ coverage target

## 📚 Resources

### Documentation
- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand](https://github.com/pmndrs/zustand)
- [Headless UI](https://headlessui.com/)

### Accessibility
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [React Accessibility](https://reactjs.org/docs/accessibility.html)
- [Testing Library](https://testing-library.com/docs/guiding-principles)

---

**Built with ❤️ using Next.js, TypeScript, and Tailwind CSS**
