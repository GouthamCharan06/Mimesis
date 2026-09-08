import "./globals.css";

export const metadata = {
  title: "Mimesis - Interactive Podcast Studio",
  description: "Agentic Interactive Podcast Platform grounded by Parallel Search MCP",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950 text-zinc-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
