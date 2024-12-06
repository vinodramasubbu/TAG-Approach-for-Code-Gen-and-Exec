SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[insurance](
	[age] [tinyint] NOT NULL,
	[sex] [nvarchar](50) NOT NULL,
	[bmi] [float] NOT NULL,
	[children] [tinyint] NOT NULL,
	[smoker] [nvarchar](50) NOT NULL,
	[region] [nvarchar](50) NOT NULL,
	[charges] [float] NOT NULL
) ON [PRIMARY]
GO
