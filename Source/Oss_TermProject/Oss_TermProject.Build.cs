// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class Oss_TermProject : ModuleRules
{
	public Oss_TermProject(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"Oss_TermProject",
			"Oss_TermProject/Variant_Platforming",
			"Oss_TermProject/Variant_Platforming/Animation",
			"Oss_TermProject/Variant_Combat",
			"Oss_TermProject/Variant_Combat/AI",
			"Oss_TermProject/Variant_Combat/Animation",
			"Oss_TermProject/Variant_Combat/Gameplay",
			"Oss_TermProject/Variant_Combat/Interfaces",
			"Oss_TermProject/Variant_Combat/UI",
			"Oss_TermProject/Variant_SideScrolling",
			"Oss_TermProject/Variant_SideScrolling/AI",
			"Oss_TermProject/Variant_SideScrolling/Gameplay",
			"Oss_TermProject/Variant_SideScrolling/Interfaces",
			"Oss_TermProject/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
