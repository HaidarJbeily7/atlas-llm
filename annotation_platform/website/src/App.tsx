import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Models from './pages/Models';
import Probes from './pages/Probes';
import Findings from './pages/Findings';
import Compliance from './pages/Compliance';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="models" element={<Models />} />
          <Route path="probes" element={<Probes />} />
          <Route path="findings" element={<Findings />} />
          <Route path="compliance" element={<Compliance />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
